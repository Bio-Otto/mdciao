# todo check that mdtraj's license allows for this
import numpy as _np
import mdtraj as _md
from mdtraj.utils import ensure_type
import itertools
from mdtraj.utils.six import string_types
from mdtraj.utils.six.moves import xrange
from mdtraj.core import element
def compute_contacts(traj, contacts='all', scheme='closest-heavy', ignore_nonprotein=True, periodic=True,
                     soft_min=False, soft_min_beta=20):
    """Compute the distance between pairs of residues in a trajectory.

    Parameters
    ----------
    traj : md.Trajectory
        An mdtraj trajectory. It must contain topology information.
    contacts : array-like, ndim=2 or 'all'
        An array containing pairs of indices (0-indexed) of residues to
        compute the contacts between, or 'all'. The string 'all' will
        select all pairs of residues separated by two or more residues
        (i.e. the i to i+1 and i to i+2 pairs will be excluded).
    scheme : {'ca', 'closest', 'closest-heavy', 'sidechain', 'sidechain-heavy'}
        scheme to determine the distance between two residues:
            'ca' : distance between two residues is given by the distance
                between their alpha carbons
            'closest' : distance is the closest distance between any
                two atoms in the residues
            'closest-heavy' : distance is the closest distance between
                any two non-hydrogen atoms in the residues
            'sidechain' : distance is the closest distance between any
                two atoms in residue sidechains
            'sidechain-heavy' : distance is the closest distance between
                any two non-hydrogen atoms in residue sidechains
    ignore_nonprotein : bool
        When using `contact==all`, don't compute contacts between
        "residues" which are not protein (i.e. do not contain an alpha
        carbon).
    periodic : bool, default=True
        If periodic is True and the trajectory contains unitcell information,
        we will compute distances under the minimum image convention.
    soft_min : bool, default=False
        If soft_min is true, we will use a diffrentiable version of
        the scheme. The exact expression used
         is d = \frac{\beta}{log\sum_i{exp(\frac{\beta}{d_i}})} where
         beta is user parameter which defaults to 20nm. The expression
         we use is copied from the plumed mindist calculator.
         http://plumed.github.io/doc-v2.0/user-doc/html/mindist.html
    soft_min_beta : float, default=20nm
        The value of beta to use for the soft_min distance option.
        Very large values might cause small contact distances to go to 0.

    Returns
    -------
    distances : np.ndarray, shape=(n_frames, n_pairs), dtype=np.float32
        Distances for each residue-residue contact in each frame
        of the trajectory
    residue_pairs : np.ndarray, shape=(n_pairs, 2), dtype=int
        Each row of this return value gives the indices of the residues
        involved in the contact. This argument mirrors the `contacts` input
        parameter. When `all` is specified as input, this return value
        gives the actual residue pairs resolved from `all`. Furthermore,
        when scheme=='ca', any contact pair supplied as input corresponding
        to a residue without an alpha carbon (e.g. HOH) is ignored from the
        input contacts list, meanings that the indexing of the
        output `distances` may not match up with the indexing of the input
        `contacts`. But the indexing of `distances` *will* match up with
        the indexing of `residue_pairs`

    Examples
    --------
    >>> # To compute the contact distance between residue 0 and 10 and
    >>> # residues 0 and 11
    >>> _md.compute_contacts(t, [[0, 10], [0, 11]])

    >>> # the itertools library can be useful to generate the arrays of indices
    >>> group_1 = [0, 1, 2]
    >>> group_2 = [10, 11]
    >>> pairs = list(itertools.product(group_1, group_2))
    >>> print(pairs)
    [(0, 10), (0, 11), (1, 10), (1, 11), (2, 10), (2, 11)]
    >>> _md.compute_contacts(t, pairs)

    See Also
    --------
    mdtraj.geometry.squareform : turn the result from this function
        into a square "contact map"
    Topology.residue : Get residues from the topology by index
    """
    if traj.topology is None:
        raise ValueError('contact calculation requires a topology')

    if isinstance(contacts, string_types):
        if contacts.lower() != 'all':
            raise ValueError('(%s) is not a valid contacts specifier' % contacts.lower())

        residue_pairs = []
        for i in xrange(traj.n_residues):
            residue_i = traj.topology.residue(i)
            if ignore_nonprotein and not any(a for a in residue_i.atoms if a.name.lower() == 'ca'):
                continue
            for j in xrange(i+3, traj.n_residues):
                residue_j = traj.topology.residue(j)
                if ignore_nonprotein and not any(a for a in residue_j.atoms if a.name.lower() == 'ca'):
                    continue
                if residue_i.chain == residue_j.chain:
                    residue_pairs.append((i, j))

        residue_pairs = _np.array(residue_pairs)
        if len(residue_pairs) == 0:
            raise ValueError('No acceptable residue pairs found')

    else:
        residue_pairs = ensure_type(_np.asarray(contacts), dtype=_np.int, ndim=2, name='contacts',
                                    shape=(None, 2), warn_on_cast=False)
        if not _np.all((residue_pairs >= 0) * (residue_pairs < traj.n_residues)):
            raise ValueError('contacts requests a residue that is not in the permitted range')

    # now the bulk of the function. This will calculate atom distances and then
    # re-work them in the required scheme to get residue distances
    scheme = scheme.lower()
    if scheme not in ['ca', 'closest', 'closest-heavy', 'sidechain', 'sidechain-heavy']:
        raise ValueError('scheme must be one of [ca, closest, closest-heavy, sidechain, sidechain-heavy]')

    if scheme == 'ca':
        if soft_min:
            import warnings
            warnings.warn("The soft_min=True option with scheme=ca gives"
                          "the same results as soft_min=False")
        filtered_residue_pairs = []
        atom_pairs = []

        for r0, r1 in residue_pairs:
            ca_atoms_0 = [a.index for a in traj.top.residue(r0).atoms if a.name.lower() == 'ca']
            ca_atoms_1 = [a.index for a in traj.top.residue(r1).atoms if a.name.lower() == 'ca']
            if len(ca_atoms_0) == 1 and len(ca_atoms_1) == 1:
                atom_pairs.append((ca_atoms_0[0], ca_atoms_1[0]))
                filtered_residue_pairs.append((r0, r1))
            elif len(ca_atoms_0) == 0 or len(ca_atoms_1) == 0:
                # residue does not contain a CA atom, skip it
                if contacts != 'all':
                    # if the user manually asked for this residue, and didn't use "all"
                    import warnings
                    warnings.warn('Ignoring contacts pair %d-%d. No alpha carbon.' % (r0, r1))
            else:
                raise ValueError('More than 1 alpha carbon detected in residue %d or %d' % (r0, r1))

        residue_pairs = _np.array(filtered_residue_pairs)
        distances = _md.compute_distances(traj, atom_pairs, periodic=periodic)
        aa_pairs = atom_pairs

    elif scheme in ['closest', 'closest-heavy', 'sidechain', 'sidechain-heavy']:
        if scheme == 'closest':
            residue_membership = [[atom.index for atom in residue.atoms]
                                  for residue in traj.topology.residues]
        elif scheme == 'closest-heavy':
            # then remove the hydrogens from the above list
            residue_membership = [[atom.index for atom in residue.atoms if not (atom.element == element.hydrogen)]
                                  for residue in traj.topology.residues]
        elif scheme == 'sidechain':
            residue_membership = [[atom.index for atom in residue.atoms if atom.is_sidechain]
                                  for residue in traj.topology.residues]
        elif scheme == 'sidechain-heavy':
            # then remove the hydrogens from the above list
            residue_membership = [[atom.index for atom in residue.atoms if atom.is_sidechain and not (atom.element == element.hydrogen)]
                                  for residue in traj.topology.residues]

        residue_lens = [len(ainds) for ainds in residue_membership]

        atom_pairs = []
        n_atom_pairs_per_residue_pair = []
        for pair in residue_pairs:
            atom_pairs.extend(list(itertools.product(residue_membership[pair[0]], residue_membership[pair[1]])))
            n_atom_pairs_per_residue_pair.append(residue_lens[pair[0]] * residue_lens[pair[1]])

        atom_distances = _md.compute_distances(traj, atom_pairs, periodic=periodic)

        # now squash the results based on residue membership
        n_residue_pairs = len(residue_pairs)
        distances = _np.zeros((len(traj), n_residue_pairs), dtype=_np.float32)
        n_atom_pairs_per_residue_pair = _np.asarray(n_atom_pairs_per_residue_pair)

        aa_pairs = []
        for i in xrange(n_residue_pairs):
            index = int(_np.sum(n_atom_pairs_per_residue_pair[:i]))
            n = n_atom_pairs_per_residue_pair[i]
            if not soft_min:
                idx_min = atom_distances[:, index : index + n].argmin(axis=1)
                aa_pairs.append(_np.array(atom_pairs[index: index + n])[idx_min])
                distances[:, i] = atom_distances[:, index : index + n].min(axis=1)
            else:
                distances[:, i] = soft_min_beta / \
                                  _np.log(_np.sum(_np.exp(soft_min_beta /
                                                       atom_distances[:, index : index + n]), axis=1))

    else:
        raise ValueError('This is not supposed to happen!')

    return distances, residue_pairs, _np.hstack(aa_pairs)