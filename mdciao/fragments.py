import numpy as _np

from mdtraj.core.residue_names import \
    _AMINO_ACID_CODES

from .residue_and_atom_utils import \
    find_AA as _find_AA,\
    _parse_and_list_AAs_input

from .bond_utils import \
    top2residue_bond_matrix

from .list_utils import \
    in_what_N_fragments as _in_what_N_fragments, \
    join_lists as _join_lists, \
    in_what_fragment as _in_what_fragment, \
    rangeexpand as _rangeexpand

from .str_and_dict_utils import \
    choose_between_good_and_better_strings as _choose_between_good_and_better_strings, \
    match_dict_by_patterns as _match_dict_by_patterns

from  pandas import \
    unique as _pandas_unique

from msmtools.estimation import \
    connected_sets as _connected_sets

abc = "abcdefghijklmnopqrst"

def _print_frag(frag_idx, top, fragment, fragment_desc='fragment',
                idx2label=None,
                return_string=False, **print_kwargs):
    """
    For pretty-printing of fragments of an :obj:`mtraj.topology`

    Parameters
    ----------
    frag_idx: int or str
        Index or name of the fragment to be printed
    top: :obj:`mdtraj.Topology`
        Topology in which the fragment appears
    fragment: iterable of indices
        The fragment in question, with zero-indexed residue indices
    fragment_desc: str, default is "fragment"
        Who to call the fragments, e.g. segment, block, monomer, chain
    idx2label : iterable or dictionary
        Pass along any consensus labels here
    return_string: bool, default is False
        Instead of printing, return the string
    print_kwargs:
        Optional keyword arguments to pass to the print function, e.g. "end=","" and such

    Returns
    -------
    None or str, see return_string option

    """
    maplabel_first, maplabel_last = "", ""
    try:
        if idx2label is not None:
            maplabel_first = _choose_between_good_and_better_strings(None,idx2label[fragment[0]],fmt="@%s")
            maplabel_last =  _choose_between_good_and_better_strings(None,idx2label[fragment[-1]],fmt="@%s")

        resfirst = "%8s%-10s"%(top.residue(fragment[0]), maplabel_first)
        reslast =  "%8s%-10s"%(top.residue(fragment[-1]), maplabel_last)
        istr = "%s %6s with %4u AAs %8s%-10s (%4u) - %8s%-10s (%-4u) (%s) " % \
               (fragment_desc, str(frag_idx), len(fragment),
                #resfirst,
                top.residue(fragment[0]), maplabel_first,
                top.residue(fragment[0]).index,
                #reslast,
                top.residue(fragment[-1]), maplabel_last,
                top.residue(fragment[-1]).index,
                str(frag_idx))
    except:
        print(fragment)
        raise
    if return_string:
        return istr
    else:
        print(istr, **print_kwargs)


def get_fragments(top,
                  method='lig_resSeq+',
                  fragment_breaker_fullresname=None,
                  atoms=False,
                  verbose=True,
                  join_fragments=None,
                  **kwargs_per_residue_fragment_picker):
    """
    Given an :obj:`mdtraj.Topology` return its residues grouped into fragments using different methods.

    Parameters
    ----------
    top : :py:class:`mdtraj.Topology`
    method : str, default is 'resSeq'
        The method passed will be the basis for creating fragments. Check the following options
        with the example sequence "…-A27,Lig28,K29-…-W40,D45-…-W50,CYSP51,GDP52"
        - 'resSeq'
            breaks at jumps in resSeq entry:
            […A27,Lig28,K29,…,W40],[D45,…,W50,CYSP51,GDP52]
        - 'resSeq+'
            breaks only at negative jumps in resSeq:
            […A27,Lig28,K29,…,W40,D45,…,W50,CYSP51,GDP52]
        - ‘bonds’
            breaks when residues are not connected by bonds, ignores resSeq:
            […A27][Lig28],[K29,…,W40],[D45,…,W50],[CYSP51],[GDP52]
            notice that because phosphorylated CYSP51 didn't get a
            bond in the topology, it's considered a ligand
        - 'resSeq_bonds'
            breaks at resSeq jumps and at missing bonds
        - 'lig_resSeq+'
            Like resSeq+ but put's any non-AA residue into it's own fragment.
            […A27][Lig28],[K29,…,W40],[D45,…,W50,CYSP51],[GDP52]
        - 'chains'
            breaks into chains of the PDB file/entry
        - None or 'None'
            all residues are in one fragment, fragment 0
    fragment_breaker_fullresname : list
        list of full residue names. Example - GLU30 that will be used to break fragments,
        so that [R1, R2, ... GLU30,...R10, R11] will be broken into [R1, R2, ...], [GLU30,...,R10,R11]
    atoms : boolean, optional
        Instead of returning residue indices, retun atom indices
    join_fragments : list of lists
        List of lists of integer fragment idxs which are to be joined together.
        (After splitting them according to "methods")
        Duplicate entries in any inner list will be removed.
        One fragment idx cannot appear in more than one inner list, otherwise program throws an error.
    verbose : boolean, optional

    kwargs_per_residue_fragment_picker : optional
        additional arguments

    Returns
    -------
    List of integer arrays
        Each array within the list has the residue indices of each fragment.
        These fragments do not have overlap. Their union contains all indices

    """

    _assert_method_allowed(method)

    # Auto detect fragments by resSeq
    old = top.residue(0).resSeq
    fragments_resSeq = [[]]
    for ii, rr in enumerate(top.residues):
        delta = _np.abs(rr.resSeq - old)
        # print(delta, ii, rr, end=" ")
        if delta <= 1:
            # print("appending")
            fragments_resSeq[-1].append(ii)
        else:
            # print("new")
            fragments_resSeq.append([ii])
        old = rr.resSeq

    if method=="resSeq":
        fragments = fragments_resSeq
    elif method=='resSeq_bonds':
        residue_bond_matrix = top2residue_bond_matrix(top, verbose=False,
                                                      force_resSeq_breaks=True)
        fragments = _connected_sets(residue_bond_matrix)
    elif method=='bonds':
        residue_bond_matrix = top2residue_bond_matrix(top, verbose=False,
                                                      force_resSeq_breaks=False)
        fragments = _connected_sets(residue_bond_matrix)
        fragments = [fragments[ii] for ii in _np.argsort([fr[0] for fr in fragments])]
    elif method == "chains":
        fragments = [[rr.index for rr in ichain.residues] for ichain in top.chains]
    elif method == "resSeq+":
        fragments = _get_fragments_resSeq_plus(top, fragments_resSeq)
    elif method == "lig_resSeq+":
        fragments = _get_fragments_resSeq_plus(top, fragments_resSeq)
        for rr in top.residues:
            if rr.name[:3] not in _AMINO_ACID_CODES.keys():
                frag_idx = _in_what_fragment(rr.index,fragments)
                if len(fragments[frag_idx])>1:
                    list_for_removing=list(fragments[frag_idx])
                    list_for_removing.remove(rr.index)
                    fragments[frag_idx]=_np.array(list_for_removing)
                    fragments.append([rr.index])


    # TODO check why this is not equivalent to "bonds" in the test_file
    elif method == 'molecules':
        raise NotImplementedError("method 'molecules' is not fully implemented yet")
        #fragments = [_np.unique([aa.residue.index for aa in iset]) for iset in top.find_molecules()]
    elif method == 'molecules_resSeq+':
        raise NotImplementedError("method 'molecules_resSeq+' is not fully implemented yet")
        """
        _molecules = top.find_molecules()
        _fragments = [_np.unique([aa.residue.index for aa in iset]) for iset in _molecules]
        _resSeqs =   [[top.residue(idx).resSeq for idx in ifrag] for ifrag in _fragments]
        _negjumps =  [_np.diff(_iresSeq) for _iresSeq in _resSeqs]
        fragments = []
        for ii, (ifrag, ijumps) in enumerate(zip(_fragments, _negjumps)):
            if all(ijumps>0):
                fragments.append(ifrag)
            else:
                offset = 0
                for kk, jj in enumerate(_np.argwhere(ijumps<0)):
                    print(ii, jj)
                    jj = int(jj)
                    #print(top.residue(ifrag[jj]), top.residue(ifrag[jj+1]))
                    offset+=jj
                    fragments.append(ifrag[:jj+1])
                    fragments.append(ifrag[jj+1:])
                    if kk>1:
                        raise Exception
        #print(_negjumps)
        """
    elif str(method).lower() == "none":
        fragments = [_np.arange(top.n_residues)]

    fragments = [fragments[ii] for ii in _np.argsort([ifrag[0] for ifrag in fragments])]
    # Inform of the first result
    if verbose:
        print("Auto-detected fragments with method %s"%str(method))
        for ii, iseg in enumerate(fragments):
            end='\n'
            ri, rj = [top.residue(ii) for ii in [iseg[0],iseg[-1]]]
            if rj.resSeq-ri.resSeq!=len(iseg)-1:
                #print(ii, rj.resSeq-ri.resSeq, len(iseg)-1)
                end='resSeq jumps\n'
            _print_frag(ii, top, iseg, end=end)
    # Join if necessary
    if join_fragments is not None:
        fragments = _join_lists(fragments, join_fragments)
        print("Joined Fragments")
        for ii, iseg in enumerate(fragments):
            _print_frag(ii, top, iseg)

    if fragment_breaker_fullresname is not None:
        if isinstance(fragment_breaker_fullresname,str):
            fragment_breaker_fullresname=[fragment_breaker_fullresname]
        for breaker in fragment_breaker_fullresname:
            residxs, fragidx = per_residue_fragment_picker(breaker, fragments, top,
                                                           **kwargs_per_residue_fragment_picker)
            idx = residxs[0]
            ifrag = fragidx[0]
            if idx is None:
                print("The fragment breaker %s appears nowhere" % breaker)
                # raise ValueError
            else:
                idx_split = _np.argwhere(idx ==_np.array(fragments[ifrag])).squeeze()
                #print('%s (index %s) found in position %s of frag %s%s' % (breaker, idx, idx_split, ifrag, fragments[ifrag]))
                subfrags = [fragments[ifrag][:idx_split], fragments[ifrag][idx_split:]]
                print("New fragments after breaker %s:" % breaker)
                if idx_split>0:
                    #print("now breaking up into", subfrags)
                    fragments = fragments[:ifrag] + subfrags + fragments[ifrag + 1:]
                    for ii, ifrag in enumerate(fragments):
                        _print_frag(ii, top, ifrag)
                else:
                    print("Not using it since it already was a fragment breaker in frag %s"%ifrag)
            print()
            # raise ValueError(idx)

    if not atoms:
        return fragments
    else:
        return [_np.hstack([[aa.index for aa in top.residue(ii).atoms] for ii in frag]) for frag in fragments]

def _get_fragments_resSeq_plus(top, fragments_resSeq):
    to_join = [[0]]
    for ii, ifrag in enumerate(fragments_resSeq[:-1]):
        r1 = top.residue(ifrag[-1])
        r2 = top.residue(fragments_resSeq[ii + 1][0])
        if r1.resSeq < r2.resSeq:
            to_join[-1].append(ii + 1)
        else:
            to_join.append([ii + 1])

    return _join_lists(fragments_resSeq, [tj for tj in to_join if len(tj) > 1])


_allowed_fragment_methods = ['resSeq',
                             'resSeq+',
                             'lig_resSeq+',
                             'bonds',
                             'resSeq_bonds',
                             'chains',
                             "None",
                             ]
def overview(topology,
             methods=['all'],
             AAs=None,
             ):

    """
    Prints the fragments created and their corresponding methods

    Parameters
    ----------
    topology :  :py:class:`mdtraj.Topology`
    methods : str or list of strings
                method(s) to be used for obtaining fragments


    Returns
    -------
    None
    prints the output from the get_fragments(), using the specified method(s)

    """

    if isinstance(methods,str):
        methods = [methods]

    if methods[0].lower() == 'all':
        try_methods = _allowed_fragment_methods
    else:
        for method in methods:
            _assert_method_allowed(method)
        try_methods = methods

    for method in try_methods:
        get_fragments(topology,
                      method=method)
        print()

    _parse_and_list_AAs_input(AAs, topology)

def _assert_method_allowed(method):
    assert str(method) in _allowed_fragment_methods, ('input method %s is not known. ' \
                                                 'Know methods are %s ' %
                                                 (method, "\n".join(_allowed_fragment_methods)))

def _rangeexpand_residues2residxs(range_as_str, fragments, top,
                                  interpret_as_res_idxs=False,
                                  sort=False,
                                  allow_empty_ranges=False,
                                  **per_residue_fragment_picker_kwargs):
    r"""
    Generalized range-expander (range-expander(2-5,7)=2,3,4,5,7 for a string containing
    residue descriptors.

    To dis-ambiguate descriptors, a fragment definition and a topology are needed

    Note
    ----
    The input (= compressed range) is very flexible and accepts
    mixed descriptors and wildcards, eg: GLU*,ARG*,GDP*,LEU394,380-385 is a valid range

    Wildcards use the full resnames, i.e. E* is NOT equivalent to GLU*

    Be aware, though, that wildcards are very powerful easily "grab" a lot of
    residues, leading to long calculations and large outputs

    Parameters
    ----------
    range_as_str : string
    fragments : list of iterable of residue indices
    top : :mdtraj:`Topology` object
    interpret_as_res_idxs : bool, default is False
        If True, indices without residue names ("380-385") values will be interpreted as
        residue indices, not resdiue sequential indices
    sort : bool
        sort the expanded range on return
    per_residue_fragment_picker_kwargs:
        Optional parameters for :obj:`per_residue_fragment_picker`

    Returns
    -------
    residxs_out = list of unique residue indices
    """
    residxs_out = []
    #print("For the range", range_as_str)
    for r in range_as_str.split(','):
        assert not r.startswith("-")
        if "*" in r or "?" in r:
            assert "-" not in r
            filtered = _find_AA(top, r)
            if len(filtered)==0:
                raise ValueError("The input range contains '%s' which "
                                 "returns no residues!"%r)
            residxs_out.extend(_find_AA(top,r))
        else:
            resnames = r.split('-')
            assert len(resnames) >=1
            if interpret_as_res_idxs:
                residx_pair = [int(rr) for rr in resnames]
            else:
                residx_pair, __ = per_residue_fragment_picker(resnames, fragments, top,
                                                              **per_residue_fragment_picker_kwargs)
                if None in residx_pair:
                    raise ValueError("The input range contains '%s' which "
                                     "returns an untreatable range %s!" % (r, residx_pair))
            residxs_out.extend(_np.arange(residx_pair[0],
                                      residx_pair[-1] + 1))

    if sort:
        residxs_out = sorted(residxs_out)

    residxs_out = _pandas_unique(residxs_out)
    return residxs_out

#TODO consider renaming
#TODO consider moving elswhere
def per_residue_fragment_picker(residue_descriptors,
                                fragments, top,
                                pick_this_fragment_by_default=None,
                                fragment_names=None,
                                additional_naming_dicts=None,
                                extra_string_info='',
                                ):
    r"""
    This function returns the fragment idxs and the residue idxs based on residue name/residue index.
    If a residue is present in multiple fragments, the function asks the user to choose the fragment, for which
    the residue idxs is reporte

    :param residue_descriptors: string or list of of strings
           AAs of the form of "GLU30" or "E30" or 30, can be mixed
    :param fragments: iterable of iterables of integers
            The integers in the iterables of 'fragments' represent residue indices of that fragment
    :param top: :py:class:`mdtraj.Topology`
    :param pick_this_fragment_by_default: None or integer.
            Pick this fragment withouth asking in case of ambiguity. If None, the user will we prompted
    :param fragment_names: list of strings providing informative names for the input fragments
    :param extra_string_info: string with any additional info to be printed in case of ambiguity
    :return: two dictionaries, resdesc2residxs and resdesc2fragidxs. If the AA is not found then the
                dictionaries for that key contain None, e.g. resdesc2residxs[notfoundAA]=None

    Returns
    -------
    residxs, fragidxs,
        lists of integers

    """
    residxs = []
    fragidxs = []
    last_answer = 0

    #TODO break the iteration in this method into a separate method. Same AAcode in different fragments will overwrite
    # each other
    if isinstance(residue_descriptors, (str, int)):
        residue_descriptors = [residue_descriptors]

    for key in residue_descriptors:
        cands = _find_AA(top, str(key))
        cand_fragments = _in_what_N_fragments(cands, fragments)
        # TODO refactor into smaller methods
        if len(cands) == 0:
            print("No residue found with descriptor %s"%key)
            residxs.append(None)
            fragidxs.append(None)
        elif len(cands) == 1 :
            residxs.append(cands[0])
            fragidxs.append(cand_fragments[0])
        else:
            istr = "ambiguous definition for AA %s" % key
            istr += extra_string_info
            for cc, ss, char in zip(cands, cand_fragments,abc):
                fname = " "
                if fragment_names is not None:
                    fname = ' (%s) ' % fragment_names[ss]
                istr = '%s) %10s in fragment %2u%swith residue index %2u'%(char, top.residue(cc),ss, fname, cc)
                if additional_naming_dicts is not None:
                    extra=''
                    for key1, val1 in additional_naming_dicts.items():
                        if cc in val1.keys() and val1[cc] is not None:
                            extra +='%s: %s '%(key1,val1[cc])
                    if len(extra)>0:
                        istr = istr + ' (%s)'%extra.rstrip(" ")
                print(istr)
            if pick_this_fragment_by_default is None:
                prompt =  "input one fragment idx (out of %s) and press enter.\n" \
                          "Leave empty and hit enter to repeat last option [%s]\n" \
                          "Use letters in case of repeated fragment index\n" % ([int(ii) for ii in cand_fragments], last_answer)

                answer = input(prompt)
            else:
                answer = str(pick_this_fragment_by_default)
                print("Automatically picked fragment %u" % pick_this_fragment_by_default)

            if len(answer) == 0:
                answer = last_answer
                cands = cands[_np.argwhere([answer == ii for ii in cand_fragments]).squeeze()]
            elif answer.isdigit():
                answer = int(answer)
                if answer in cand_fragments:
                    cands = cands[_np.argwhere([answer == ii for ii in cand_fragments]).squeeze()]
            elif answer.isalpha() and answer in abc:
                idx = abc.find(answer)
                answer = cand_fragments[idx]
                cands  = cands[idx]
            else:
                raise ValueError("%s is not a possible answer"%answer)
                #TODO implent k for keeping this answer from now on

            assert answer in cand_fragments, (
                        "Your answer has to be an integer in the of the fragment list %s" % cand_fragments)
            last_answer = answer

            residxs.append(int(cands))  # this should be an integer
            fragidxs.append(int(answer)) #ditto

    return residxs, fragidxs

def _check_if_subfragment(sub_frag, fragname, fragments, top,
                          map_conlab=None,
                          keep_all=False):
    r"""
    Input an iterable of integers representing a fragment check if
    it clashes with other fragment definitions.

    Prompt for a choice in case it is necessary


    Example
    -------
    Let's assume the BW-nomenclature tells us that TM6 is [0,1,2,3]
    and we have already divided the topology into fragments
    using :obj:`get_fragments`, with method "resSeq+", meaning
    we have fragments for the receptor, Ga,Gb,Gg

    The purpusose is to check whether the BW-fragmentation is
    contained in the previous fragmentation:
    * [0,1,2,3] and :obj:`fragments`=[[0,1,2,3,4,6], [7,8,9]]
    is not a clash, bc TM6 is contained in fragments[0]
    * [0,1,2,3] and :obj:`fragments`=[[0,1],[2,3],[4,5,6,7,8]]
    is a clash. In this case the user will be prompted to choose
    which subset of "TM6" to keep:
     * "0": [0,1]
     * "1": [2,3]
     * "0-1" [0,1,2,3]


    Parameters
    ----------
    sub_frag : iterable of integers
    fragname : str
    fragments : iterable of iterables of integers
    top : :obj:`mdtraj.Trajectory`object
    map_conlab : list or dict, default is None
        maps residue idxs to consensus labels

    Returns
    -------
    tokeep = 1D numpy array
        If no clashes were found, this will be contain the same residues as
        :obj:`sub_frag` without prompting the user.
        Otherwise, the user has to input whether to leave the definition intact
        or pick a sub-set
    """
    # Get the fragment idxs of all residues in this fragment
    ifrags = [_in_what_fragment(idx, fragments) for idx in sub_frag]

    frag_cands = [ifrag for ifrag in _pandas_unique(ifrags) if ifrag is not None]
    if len(frag_cands) > 1 and not keep_all:
        # This only happens if more than one fragment is present
        _print_frag(fragname, top, sub_frag, fragment_desc='',
                    idx2label=map_conlab)
        print("  %s clashes with other fragment definitions"%fragname)
        for jj in frag_cands:
            istr = _print_frag(jj, top, fragments[jj],
                               fragment_desc="   input fragment",
                               return_string=True)
            n_in_fragment = len(_np.intersect1d(sub_frag, fragments[jj]))
            if n_in_fragment < len(fragments[jj]):
                istr += "%u residues outside %s" % (len(fragments[jj]) - n_in_fragment, fragname)
            print(istr)
        answr = input("Input what fragment idxs to include into %s  (fmt = 1 or 1-4, or 1,3):" % fragname)
        answr = _rangeexpand(answr)
        assert all([idx in ifrags for idx in answr])
        tokeep = _np.hstack([idx for ii, idx in enumerate(sub_frag) if ifrags[ii] in answr]).tolist()
        if len(tokeep) >= len(ifrags):
            raise ValueError("Cannot keep these fragments %s!" % (str(answr)))
        return tokeep
    else:
        return sub_frag

def _fragments_strings_to_fragments(fragment_input, top, verbose=False):
    r"""
    Method to help implement the input options wrt
    to fragments of :obj:`parsers.parser_for_interface`

    Check the documentation of interface (-h) for more details

    Check also :obj:`rangeexpand` to understand the expressions


    Parameters
    ----------
    fragment_input : list of strings
        Many cases are possible
        * ["consensus"] : fragment using "resSeq+"
        and return user_wants_consensus as True
        * [method] : fragment using "method"
        (see :obj:`get_fragments`) and return
        user_wants_consensus as False
        * [['exp1']] : this str represents the
        residues in one fragment (eg. "0-3,5" : 0,1,2,3,5).
        Assume that the missing residues the other fragment.
        Return the two fragments and user_wants_consensus as False
        * [["exp1"],
           ["exp2"],
           [...]]
        These strs are the fragments expressed as residue
        indices. Evaluate them and return them. Return
        user_wants_consensus as False
        * None or "None"

    top : :obj:`mdtraj.Topology`

    Returns
    -------
    fragments_as_residue_idxs, user_wants_consensus

    """
    user_wants_consensus = False
    assert isinstance(fragment_input,list)
    if ("".join(fragment_input).replace("-","").replace(",","")).isnumeric():
        method = "user input by residue index"
        # What we have is list residue idxs as strings like 0-100, 101-200, 201-300
        fragments_as_residue_idxs =[_rangeexpand(ifrag.strip(",")) for ifrag in fragment_input]
        for ii, ifrag in enumerate(fragments_as_residue_idxs):
            if not all([aa in range(top.n_residues) for aa in ifrag]):
                print("Fragment %u has idxs outside of the geometry (total n_residues %u): %s"%(ii, top.n_residues,
                                                                         set(ifrag).difference(range(top.n_residues))))

        if len(fragment_input)==1:
            assert isinstance(fragment_input[0],str)
            method += "(only one fragment provided, assuming the rest of residues are fragment 2)"
            fragments_as_residue_idxs.append(_np.delete(_np.arange(top.n_residues), fragments_as_residue_idxs[0]))
    elif len(fragment_input)==1:
        if fragment_input[0].lower()=="consensus":
            user_wants_consensus = True
            method = 'resSeq+ (for later user_wants_consensus labelling)'
            fragments_as_residue_idxs = get_fragments(top, method='resSeq+',
                                                      verbose=False)
        else:
            method = fragment_input[0]
            fragments_as_residue_idxs = get_fragments(top, method=method,
                                                      verbose=False)
    if verbose:
        print("Using method '%s' these fragments were found"%method)
        for ii, ifrag in enumerate(fragments_as_residue_idxs):
            _print_frag(ii, top, ifrag)

    return fragments_as_residue_idxs, user_wants_consensus

def _frag_list_2_frag_groups(frag_list,
                             frag_idxs_group_1=None,
                             frag_idxs_group_2=None,
                             verbose=False):
    r"""
    Automagically find out the user wants to define
    two fragments out of list of fragments. This is used
    by CLTs interface

    Promt the user when disambguation is needed.

    Parameters
    ----------
    frag_list : list
        list of fragments, defined as residue indices
    frag_idxs_group_1 : iterable of ints, or str default is None
        When str, it has to be a rangeexpand exprs, e.g. 2-5,10
    frag_idxs_group_2 : iterable of ints, or str default is None


    Returns
    -------
    groups_as_residxs, groups_as_fragidxs

    """

    if verbose:
        for ii, ifrag in enumerate(frag_list):
            print("frag %u: %u-%u"%(ii, ifrag[0],ifrag[-1]))

    if len(frag_list) == 2 and \
            frag_idxs_group_1 is None and \
            frag_idxs_group_2 is None:
        print("Only two fragments detected with no values for frag_idxs_group_1 and frag_idxs_group_2.\n"
              "Setting frag_idxs_group_1=0 and frag_idxs_group_2=1")
        groups_as_fragidxs = [[0], [1]]
        #TODO I don't think i need the check for None in the frag_idxs_groups, right?
    else:
        groups_as_fragidxs = [frag_idxs_group_1, frag_idxs_group_2]
        for ii, ifrag_idxs in enumerate(groups_as_fragidxs):
            if ifrag_idxs is None:
                groups_as_fragidxs[ii] = _rangeexpand(input('Input group of fragments (e.g. 0,3 or 2-4,6) for group %u: ' % (ii + 1)))
            elif isinstance(ifrag_idxs, str):
                groups_as_fragidxs[ii] = _rangeexpand(ifrag_idxs)
    groups_as_residxs = [sorted(_np.hstack([frag_list[ii] for ii in iint])) for iint in
                            groups_as_fragidxs]

    return groups_as_residxs, groups_as_fragidxs

def frag_dict_2_frag_groups(frag_defs_dict, ng=2,
                            verbose=False):
    r"""
    Input a dictionary of fragment definitions, keyed by
    whatever and valued with residue idxs and prompt
    the user how to re-group them

    It wraps around :obj:`_match_dict_by_patterns` to
    under the hood

    TODO: refactor into str_and_dict_utils
    TODO: It will be mostly used with fragments so it's better here for the API? IDK

    Parameters
    ----------
    frag_defs_dict : dict
        Fragment definitions in residue idxs
    ng : int, default is 2
        wanted number of groups

    Returns
    -------
    groups_as_residue_idxs, groups_as_keys

    groups_as_residue_idxs : list of len ng
        Contains ng arrays with the concatenated
        and sorted residues in each group
    groups_as_keys : list of len ng
        Contains ng lists with the keys
        of :obj:`frag_defs_dict` in each of groups
    """

    groups_as_keys = []
    groups_as_residue_idxs = []
    if verbose:
        for key, val in frag_defs_dict.items():
            print("%s: %u-%u"%(key, val[0],val[-1]))
    for ii in range(1, ng + 1):
        print("group %u: " % ii, end='')
        answer = input(
            "Input a list of comma-separated posix-expressions.\n"
            "Prepend with '-' to exclude, e.g. 'TM*,-TM2,H8' to grab all TMs and H8, but exclude TM2)\n").replace(
            " ", "").strip("'").strip('"')
        igroup, res_idxs_in_group = _match_dict_by_patterns(answer, frag_defs_dict)
        groups_as_keys.append([ilab for ilab in frag_defs_dict.keys() if ilab in igroup])
        groups_as_residue_idxs.append(sorted(res_idxs_in_group))
        print(', '.join(groups_as_keys[-1]))

    return groups_as_residue_idxs, groups_as_keys

_my_frag_colors=[
         'magenta',
         'yellow',
         'lime',
         'maroon',
         'navy',
         'olive',
         'orange',
         'purple',
         'teal',
]