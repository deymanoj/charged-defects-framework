import os
import argparse
import numpy as np
from pymatgen.io.vasp.inputs import Poscar
from pymatgen import Structure
from pymatgen.core.operations import SymmOp


def get_rotation_matrix(axis, theta):
    
    """
    Copied from MPInterfaces with some slight modification.
    Find the rotation matrix associated with counterclockwise rotation
    about the given axis by theta radians, using Euler–Rodrigues formula.
    Credit: http://stackoverflow.com/users/190597/unutbu
        
    Parameters
    ----------
    axis (list): rotation axis of the form [x, y, z]
    theta (float): rotational angle in radians
    
    Returns
    -------
    (array) Rotation matrix.
        
    """

    axis = np.array(list(axis))
    axis = axis / np.linalg.norm(axis)
    axis *= -np.sin(theta/2.0)
    a = np.cos(theta/2.0)
    b, c, d = tuple(axis.tolist())
    aa, bb, cc, dd = a*a, b*b, c*c, d*d
    bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
    
    return np.array([[aa+bb-cc-dd, 2*(bc+ad), 2*(bd-ac)],
                     [2*(bc-ad), aa+cc-bb-dd, 2*(cd+ab)],
                     [2*(bd+ac), 2*(cd-ab), aa+dd-bb-cc]])
					 

def align_axis(structure, axis='c', direction=(0, 0, 1)):
    
    """
    Copied from MPInterfaces with some slight modification.
    Rotates a structure so that the specified axis is along
    the [001] direction. This is useful for adding vacuum, and
    in general for using vasp compiled with no z-axis relaxation.
        
    Parameters
    ----------
    structure (Structure): Pymatgen Structure object to rotate.
    axis: Axis to be rotated. Can be 'a', 'b', 'c', or a 1x3 vector.
    direction (vector): Final axis to be rotated to.
    
    Returns
    -------
    (Structure) Structure object rotated to align axis along direction.  
        
    """

    if axis == 'a':
        axis = structure.lattice._matrix[0]
    elif axis == 'b':
        axis = structure.lattice._matrix[1]
    elif axis == 'c':
        axis = structure.lattice._matrix[2]
    rot_axis = np.cross(axis, direction)
    if not(rot_axis[0] == 0 and rot_axis[1] == 0):
        theta = (np.arccos(np.dot(axis, direction) / 
                 (np.linalg.norm(axis) * np.linalg.norm(direction))))
        R = get_rotation_matrix(rot_axis, theta)
        rotation = SymmOp.from_rotation_and_translation(rotation_matrix=R)
        structure.apply_operation(rotation)
#    if axis == 'c' and direction == (0, 0, 1):
#        structure.lattice._matrix[2][2] = abs(structure.lattice._matrix[2][2])

    return structure


def center_slab(structure):
    
    """
    Copied from MPInterfaces with some slight modification.
    Centers the atoms in a slab structure around 0.5 fractional height.

    Parameters
    ----------
    structure (Structure): Structure to center
    
    Returns
    -------
    (Structure) Centered Structure object.
        
    """

    slab_center = np.average([s._fcoords[2] for s in structure.sites])
    structure.translate_sites(range(structure.num_sites), (0, 0, 0.5 - slab_center))
    
    return structure


def get_slab_thickness(structure):
    
    """
    Returns the interlayer spacing for a 2D material or slab.
        
    Parameters
    ----------
    structure (Structure): Structure to check spacing for.
    cut (float): a fractional z-coordinate that must be within the vacuum region.
    
    Returns
    -------
    (float) Spacing in Angstroms.
    
    """

    structure = align_axis(structure)
    structure = center_slab(structure)
    max_height = max([s.coords[2] for s in structure.sites])
    min_height = min([s.coords[2] for s in structure.sites])
    
    return (max_height - min_height)


def add_vacuum(structure, vacuum):
    
    """
    Copied from MPInterfaces with some slight modification.
    Adds padding to a slab or 2D material.
        
    Parameters
    ----------
    structure (Structure): Structure to add vacuum to
    vacuum (float): Vacuum thickness to add in Angstroms
    
    Returns
    -------
    (Structure) Structure object with vacuum added.
    
    """
    
    structure = align_axis(structure)
    coords = [s.coords for s in structure.sites]
    species = [s.specie for s in structure.sites]
    lattice = structure.lattice.matrix
    lattice[2][2] += vacuum
    structure = Structure(lattice, species, coords, coords_are_cartesian=True)
    
    return center_slab(structure)
	

def layer_from_bulk(struct_bulk,slabmin,slabmax):
    
    """
    Extracts a layer from a layered bulk material.
        
    Parameters
    ----------
    struct_bulk (Structure): Pymatgen Structure object of the layered bulk
    slabmin (float): fractional coord of the bottom of the layer to isolate
    slabmax (float): fractional coord of the top of the layer to isolate
    
    Returns
    -------
    (Structure) Structure object of the single layer.
    
    """

    struct_layer = struct_bulk.copy()    
    not_in_layer = [i for i,site in enumerate(struct_layer.sites) \
                          if site.c < slabmin or site.c > slabmax]    
    struct_layer.remove_sites(not_in_layer)

    return struct_layer


#def unitcell_hexagonal(vac,a0,d):
#    
#    ## HARDCODED hexagonal unitcell for MoS2
#    ## d is the layer thickness (S-S distance in this case)
#      
#    c = d + vac
#    Sz = d/2/c 
#    
#    coords = [[0.3333333333333333, 0.6666666666666667, 0.5],
#              [0.6666666666666667,  0.3333333333333333, 0.5+Sz],
#              [0.6666666666666667,  0.3333333333333333, 0.5-Sz]]
#    lattice = Lattice.from_parameters(a=a0, b=a0, c=c,
#                                      alpha=90, beta=90, gamma=120)
#    
#    return (Structure(lattice,["Mo","S","S"],coords))
#
#
#def unitcell_orthorhombic(vac,a0,d):
#    
#    ## HARDCODED orthorhombic unitcell for MoS2
#    ## d is the layer thickness (S-S distance in this case)
#      
#    c = d + vac
#    Sz = d/2/c 
#    
#    coords = [[0.0, 0.3333333333333333, 0.5],
#              [0.5, 0.8333333333333333, 0.5],
#              [0.0, 0.6666666666666667, 0.5+Sz],
#              [0.0, 0.6666666666666667, 0.5-Sz],
#              [0.5, 0.1666666666666667, 0.5+Sz],
#              [0.5, 0.1666666666666667, 0.5-Sz]]
#    lattice = Lattice.from_parameters(a=a0, b=np.sqrt(3)*a0, c=c,
#                                      alpha=90, beta=90, gamma=90)
#
#    return (Structure(lattice,["Mo","Mo","S","S","S","S"],coords))

    
if __name__ == '__main__':
    
     
    parser = argparse.ArgumentParser(description='Generate 2D unitcell.')
    parser.add_argument('path_poscar',help='path to unitcell POSCAR')
    parser.add_argument('vacuum',type=int,help='vacuum spacing')
    parser.add_argument('--from_bulk',help='extract layer from bulk?',
                        default=False,action='store_true')
    parser.add_argument('--slabmin',type=float,
                        help='fractional coord of the bottom of the layer to isolate')
    parser.add_argument('--slabmax',type=float,
                        help='fractional coord of the top of the layer to isolate')
      
    ## read in the above arguments from command line
    args = parser.parse_args()


    ## get current working directory
    ## subdirectories for different vacuum spacings will be created here
    dir_main = os.getcwd()
    
    
    poscar = Poscar.from_file(args.path_poscar, check_for_POTCAR=False) 
     
    struct = align_axis(poscar.structure)
    if args.from_bulk:
        if args.slabmin == None or args.slabmax == None:
            raise ValueError('missing slabmin and/or slabmax argument')
        else:
            struct = layer_from_bulk(struct,args.slabmin,args.slabmax)  
    slab_d = get_slab_thickness(struct)
    struct = add_vacuum(struct, args.vacuum - (struct.lattice.c - slab_d))
    struct = center_slab(struct)


    dir_sub = os.path.join(dir_main,"vac_%d"%args.vacuum)
    if not os.path.exists(dir_sub):
        os.makedirs(dir_sub)
    Poscar.write_file(Poscar(struct),os.path.join(dir_sub,"POSCARtest"))

