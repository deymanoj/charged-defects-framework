import os
import sys
import time
import argparse
import myutils
import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('agg')


def main(args):
    
    ## define a main function callable from another python script
  
    parser = argparse.ArgumentParser(description='Estimate alignment correction.')
    parser.add_argument('vref',help='path to bulk LOCPOT file')
    parser.add_argument('vdef',help='path to defect LOCPOT file')
    parser.add_argument('encut',type=int,help='cutoff energy (eV)')
    parser.add_argument('q',type=int,help='charge (conventional units)')
    parser.add_argument('--threshold_slope',type=float,default=1e-3,
                        help='threshold for determining if potential is flat')
    parser.add_argument('--threshold_C',type=float,default=1e-3,
                        help='threshold for determining if potential is aligned')
    parser.add_argument('--max_iter',type=int,default=20,
                        help='max. no. of shifts to try')
    parser.add_argument('--vfile',help='vline .dat file',default='vline-eV.dat')
    parser.add_argument('--noplots',help='do not generate plots',default=False,action='store_true')
    parser.add_argument('--allplots',help='save all plots',default=False,action='store_true')
    parser.add_argument('--logfile',help='logfile to save output to')
       
    ## read in the above arguments from command line
    args = parser.parse_args(args)
    
    
    ## set up logging
    if args.logfile:
        myLogger = myutils.setup_logging(os.path.join(os.getcwd(),args.logfile))
    else:
        myLogger = myutils.setup_logging()
    
    
    ## basic command to run sxdefectalign2d
    command = ['~/sxdefectalign2d', '--vasp',
               '--ecut', str(args.encut/13.6057), ## convert eV to Ry
               '--vref', args.vref,
               '--vdef', args.vdef]
    
    
    ## initialize the range of shift values bracketing the optimal shift
    smin, smax = -np.inf, np.inf
    shift = 0.0
    shifting = 'right'
    done = False
    counter = -1


    time0 = time.time()
    while not done and counter < args.max_iter:
        counter += 1
        ## run sxdefectalign2d with --shift <shift>
        if args.logfile:
            command1 = command + ['--shift', str(shift), '--onlyProfile', '>> %s'%args.logfile]
        else:
            command1 = command + ['--shift', str(shift), '--onlyProfile']
        os.system(' '.join(command1))
        
        ## read in the potential profiles from vline-eV.dat
        ## z  V^{model}  \DeltaV^{DFT}  V^{sr}
        data = np.loadtxt(args.vfile)
        
        ## plot potential profiles
        if not args.noplots:
            plt.figure()
            plt.plot(data[:,0],data[:,2],'r',label=r'$V_{def}-V_{bulk}$')
            plt.plot(data[:,0],data[:,1],'g',label=r'$V_{model}$')
            plt.plot(data[:,0],data[:,-1],'b',label=r'$V_{def}-V_{bulk}-V_{model}$')
            plt.xlabel("distance along z axis (bohr)")
            plt.ylabel("potential (eV)")
            plt.xlim(data[0,0],data[-1,0])
            plt.legend() 
            if args.allplots:
                plt.savefig(os.getcwd()+'/alignment_%d.png'%counter)
            else:
                plt.savefig(os.getcwd()+'/alignment.png')
            plt.close()
        
        ## assumes that the slab is in the center of the cell vertically!
        ## select datapoints corresponding to 2 bohrs at the top and bottom
        ## of the supercell (i.e. a total of 4 bohrs in the middle of vacuum)
        z1 = np.min([i for i,z in enumerate(data[:,0]) if z > 2.])
        z2 = np.min([i for i,z in enumerate(data[:,0]) if z > (data[-1,0]-2.)])
        
        ## fit straight lines through each subset of datapoints
        m1,C1 = np.polyfit(data[:z1,0],data[:z1,-1],1)
        m2,C2 = np.polyfit(data[z2:,0],data[z2:,-1],1)
        myLogger.debug("Slopes: %.8f %.8f; Intercepts: %.8f %.8f"%(m1,m2,C1,C2))
        
        ## check the slopes and intercepts of the lines
        ## and shift the charge along z until the lines are flat
        if (abs(m1) < args.threshold_slope and abs(m2) < args.threshold_slope
            and abs(C1-C2) < args.threshold_C):
            done = True
            break
        elif m1*m2 < 0:
            myLogger.info("undetermined...make a tiny shift and try again")
            if shifting == 'right':
                shift += 0.01
            else: 
                shift -= 0.01
            myLogger.info("try shift = %.8f"%shift)
        elif (m1+m2)*np.sign(args.q) > 0:
            smin = shift
            if smax == np.inf:
                shift += 1.0
            else:
                shift = (smin+smax)/2.0
            shifting = 'right'
            myLogger.debug("optimal shift is in [%.8f, %.8f]"%(smin,smax))
            myLogger.info("shift charge in +z direction; try shift = %.8f"%shift)
        elif (m1+m2)*np.sign(args.q) < 0:
            smax = shift
            if smin == -np.inf:
                shift -= 1.0
            else:
                shift = (smin+smax)/2.0
            shifting = 'left'
            myLogger.debug("optimal shift is in [%.8f, %.8f]"%(smin,smax))
            myLogger.info("shift charge in -z direction; try shift = %.8f"%shift)
    
                       
    if done:
        C_ave = (C1+C2)/2
        myLogger.info("DONE! shift = %.8f & alignment correction = %.8f"%(shift,C_ave))
        ## run sxdefectalign2d with --shift <shift> -C <C_ave> > correction
        command2 = command + ['--shift', str(shift),
                              '-C', str(C_ave),
                              '> correction']
        os.system(' '.join(command2))
    else:
        myLogger.info("Could not find optimal shift after %d tries :("%args.max_iter)
    
    myLogger.debug("Total time taken (s): %.2f"%(time.time()-time0))
    
    
if __name__ == '__main__':
    
    main(sys.argv[1:]) 
    
