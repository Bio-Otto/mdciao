import mdtraj as _md
import numpy as _np
from .aa_utils import int_from_AA_code as _int_from_AA_code, shorten_AA as _shorten_AA
from .sequence_utils import alignment_result_to_list_of_dicts as _alignment_result_to_list_of_dicts, _my_bioalign


def table2BW_by_AAcode(tablefile="GPCRmd_B2AR_nomenclature.xlsx",
                       modifications={"S262":"F264"},
                       keep_AA_code=True,
                       return_defs=False,
                       ):
    """
    Returns a dictionary of the residues and their corresponding BW notation from the excel file.

    Parameters
    ----------
    tablefile : xlsx file
        GPCRmd_B2AR nomenclature file in excel format, optional
    modifications : dictionary
        Pass the modifications required in the residue name.
        Parameter should be passed as a dictionary of the form {old name:new name}.
    keep_AA_code : boolean
        'True' if amino acid letter code is required. (Default is True).
        If True then output dictionary will have key of the form "Q26" else "26".
    return_defs : boolean
        'True' if definition lines from the file are required then. (Default is True).

    Returns
    -------

    Dictionary, list(optional)
        Dictionary with residues as key and their corresponding BW notation.
        if return_defs=false else dictionary(residue and their BW notation),
        and a list of the definition lines from the excel.

    """
    out_dict = {}
    import pandas
    df = pandas.read_excel(tablefile, header=None)

    # Locate definition lines and use their indices
    defs = []
    for ii, row in df.iterrows():
        if row[0].startswith("TM") or row[0].startswith("H8"):
            defs.append(row[0])

        else:
            out_dict[row[2]] = row[1]

    # Replace some keys
    __ = {}
    for key, val in out_dict.items():
        for patt, sub in modifications.items():
            key = key.replace(patt,sub)
        __[key] = str(val)
    out_dict = __

    # Make proper BW notation as string with trailing zeros
    out_dict = {key:'%1.2f'%float(val) for key, val in out_dict.items()}

    if keep_AA_code:
        pass
    else:
        out_dict =  {int(key[1:]):val for key, val in out_dict.items()}

    if return_defs:
        return out_dict, defs
    else:
        return out_dict


def guess_missing_BWs(input_BW_dict,top, restrict_to_residxs=None, keep_keys=False):
    """
    Interpolates the BW for residues which are not present in the nomenclature file.

    Parameters
    ----------
    input_BW_dict : dictionary
        BW dictionary with residue names as the key and their corresponding BW notation
    top : :py:class:`mdtraj.Topology`
    restrict_to_residxs: list, optional
        residue indexes for which the BW needs to be estimated. (Default value is None).

    Returns
    -------
    Dictionary
        Dictionary where the missing values are estimated. It also retains all the values from the input dictionary.

    """

    if restrict_to_residxs is None:
        restrict_to_residxs = [residue.index for residue in top.residues]

    """
    seq = ''.join([top._residues    [ii].code for ii in restrict_to_residxs])
    seq_BW =  ''.join([key[0] for key in input_BW_dict.keys()])
    ref_seq_idxs = [int_from_AA_code(key) for key in input_BW_dict.keys()]
    for alignmt in pairwise2.align.globalxx(seq, seq_BW)[:1]:
        alignment_dict = alignment_result_to_list_of_dicts(alignmt, top,
                                                            ref_seq_idxs,
                                                            #res_top_key="target_code",
                                                           #resname_key='target_resname',
                                                           #resSeq_key="target_resSeq",
                                                           #idx_key='ref_resSeq',
                                                           #re_merge_skipped_entries=False
                                                            )
        print(alignment_dict)
    return
    """
    #TODO keep this until we are sure there are no consquences
    #out_dict = {ii:None for ii in range(top.n_residues)}
    out_dict = {}
    for rr in restrict_to_residxs:
        residue = top.residue(rr)
        key = '%s%s'%(residue.code,residue.resSeq)
        try:
            (key, input_BW_dict[key])
            #print(key, input_BW_dict[key])
            out_dict[residue.index] = input_BW_dict[key]
        except KeyError:
            resSeq = _int_from_AA_code(key)
            try:
                key_above = [key for key in input_BW_dict.keys() if _int_from_AA_code(key)>resSeq][0]
                resSeq_above = _int_from_AA_code(key_above)
                delta_above = int(_np.abs([resSeq - resSeq_above]))
            except IndexError:
                delta_above = 0
            try:
                key_below = [key for key in input_BW_dict.keys() if _int_from_AA_code(key)<resSeq][-1]
                resSeq_below = _int_from_AA_code(key_below)
                delta_below = int(_np.abs([resSeq-resSeq_below]))
            except IndexError:
                delta_below = 0

            if delta_above<=delta_below:
                closest_BW_key = key_above
                delta = -delta_above
            elif delta_above>delta_below:
                closest_BW_key = key_below
                delta = delta_below
            else:
                print(delta_above, delta_below)
                raise Exception

            if residue.index in restrict_to_residxs:
                closest_BW=input_BW_dict[closest_BW_key]
                base, exp = [int(ii) for ii in closest_BW.split('.')]
                new_guessed_val = '%s.%u*'%(base,exp+delta)
                #guessed_BWs[key] = new_guessed_val
                out_dict[residue.index] = new_guessed_val
                #print(key, new_guessed_val, residue.index, residue.index in restrict_to_residxs)
            else:
                pass
                #new_guessed_val = None

            # print("closest",closest_BW_key,closest_BW, key, new_guessed_val )

    #input_BW_dict.update(guessed_BWs)

    if keep_keys:
        guessed_BWs = {}
        used_keys = []
        for res_idx, val in out_dict.items():
            new_key = _shorten_AA(top.residue(res_idx))
            if new_key in input_BW_dict.keys():
                assert val==input_BW_dict[new_key],"This should not have happened %s %s %s"%(val, new_key, input_BW_dict[new_key])
            assert new_key not in used_keys
            guessed_BWs[new_key]=val
            used_keys.append(new_key)
        return guessed_BWs
    else:
        return out_dict

class CGN_transformer(object):
    """
    Class to convert the residues in the 3SN6.pdb file to its corresponding common-Gprotein-nomenclature numbering.
    See here_ for more info.
     .. _here: https://www.mrc-lmb.cam.ac.uk/CGN/faq.html
    This object needs to read the files

    * 3SN6.pdb
    * CGN_3SNG.txt

    or equivalent files for other PDB codes

    """
    def __init__(self, ref_PDB='3SN6', ref_path='.'):
        r"""

        Parameters
        ----------
        ref_PDB: str, default is '3SN6'
            The PDB four letter code that will be used for CGN purposes
        ref_path: str,default is '.'
            The path where the needed files are
        """
        # Create dataframe with the alignment
        from pandas import read_csv as _read_csv
        from os import path as _path
        self._ref_PDB = ref_PDB

        self._DF = _read_csv(_path.join(ref_path, 'CGN_%s.txt'%ref_PDB), delimiter='\t')

        self._dict = {key: self._DF[self._DF[ref_PDB] == key]["CGN"].to_list()[0] for key in self._DF[ref_PDB].to_list()}

        try:
            self._top =_md.load(_path.join(ref_path, ref_PDB+'.pdb')).top
        except (OSError,FileNotFoundError):
            self._top = _md.load(_path.join(ref_path, ref_PDB + '.pdb.gz')).top
        seq_ref = ''.join([str(rr.code).replace("None","X") for rr in self._top.residues])[:len(self._dict)]
        seq_idxs = _np.hstack([rr.resSeq for rr in self._top.residues])[:len(self._dict)]
        keyval = [{key:val} for key,val in self._dict.items()]
        #for ii, (iseq_ref, iseq_idx) in enumerate(zip(seq_ref, seq_idxs)):
        #print(ii, iseq_ref, iseq_idx )

        self._seq_ref  = seq_ref
        self._seq_idxs = seq_idxs

        self._ref_PDB = ref_PDB

    @property
    def seq(self):
        r""" Sequence of AAs (one-letter codes) in the reference pdb file.
        If an AA has no one-letter, the letter X is used"""
        return self._seq_ref

    @property
    def seq_idxs(self):
        r""" Indices contained in the original PDB as sequence indices.
        In an :obj:`mdtraj.Topology.Residue`, this index is called 'ResSeq'"""
        return self._seq_idxs

    @property
    def AA2CGN(self):
        r"""Dictionary with AA-codes as keys, so that "G.HN.42" = AA2CGN["K25"].
        If an AA does not have a CGN-name, it is not present in the keys. """
        return self._dict

    @property
    def ref_PDB(self):
        r""" Return the PDB code used for instantiation"""

        return self._ref_PDB

        #return seq_ref, seq_idxs, self._dict

def top2CGN_by_AAcode(top, ref_CGN_tf, keep_AA_code=True,
                      restrict_to_residxs=None,
                      verbose=False):
    """
    Transforms each residue in the topology file to its corresponding CGN numbering.

    Parameters
    ----------
    top : :py:class:`mdtraj.Topology`
    ref_CGN_tf : :obj: 'nomenclature_utils.CGN_transformer' object
    keep_AA_code : boolean, optional
    restrict_to_residxs: list, optional
        residue indexes for which the BW needs to be estimated. (Default value is None).

    Returns
    -------
    Dictionary
        For each residue in the topology file, returns the corresponding CGN numbering.
        Example:    {0: 'G.HN.27',1: 'G.HN.53'}


    """

    if restrict_to_residxs is None:
        restrict_to_residxs = [residue.index for residue in top.residues]

    #out_dict = {ii:None for ii in range(top.n_residues)}
    #for ii in restrict_to_residxs:
    #    residue = top.residue(ii)
    #    AAcode = '%s%s'%(residue.code,residue.resSeq)
    #    try:
    #        out_dict[ii]=ref_CGN_tf.AA2CGN[AAcode]
    #    except KeyError:
    #        pass
    #return out_dict
    seq = ''.join([str(top.residue(ii).code).replace("None", "X") for ii in restrict_to_residxs])
    #
    res_idx2_PDB_resSeq = {}
    AA_code_seq_0_key = "AA_input"
    full_resname_seq_0_key = 'resname_input'
    resSeq_seq_0_key = "resSeq_input"
    AA_code_seq_1_key = 'AA_ref(%s)' % ref_CGN_tf.ref_PDB
    idx_seq_1_key = 'resSeq_ref(%s)' % ref_CGN_tf.ref_PDB
    idx_seq_0_key = 'idx_input'
    for alignmt in _my_bioalign(seq, ref_CGN_tf.seq)[:1]:
        #TODO this fucntion has been changed and this transformer will not work anymore
        # major bug

        list_of_alignment_dicts = _alignment_result_to_list_of_dicts(alignmt, top,
                                                                     restrict_to_residxs,
                                                                     ref_CGN_tf.seq_idxs,
                                                                     AA_code_seq_0_key=AA_code_seq_0_key,
                                                                     full_resname_seq_0_key=full_resname_seq_0_key,
                                                                     resSeq_seq_0_key=resSeq_seq_0_key,
                                                                     AA_code_seq_1_key=AA_code_seq_1_key,
                                                                     idx_seq_1_key=idx_seq_1_key,
                                                                     idx_seq_0_key=idx_seq_0_key,
                                                                     )

        if verbose:
            import pandas as pd
            from IPython.display import display
            with pd.option_context('display.max_rows', None, 'display.max_columns',
                                   None):  # more options can be specified also
                display(pd.DataFrame.from_dict(list_of_alignment_dicts))

        for idict in list_of_alignment_dicts:
            if idict["match"]==True:
                res_idx_input = idict[idx_seq_0_key]
                if res_idx_input in restrict_to_residxs:
                    match_name = '%s%s'%(idict[AA_code_seq_1_key],idict[idx_seq_1_key])
                    #print(res_idx_input,"res_idx_input",match_name)
                    res_idx2_PDB_resSeq[res_idx_input]=match_name
    out_dict = {}
    for ii in range(top.n_residues):
        try:
            out_dict[ii] = ref_CGN_tf.AA2CGN[res_idx2_PDB_resSeq[ii]]
        except KeyError:
            out_dict[ii] = None

    return out_dict
    # for key, equiv_at_ref_PDB in res_idx2_PDB_resSeq.items():
    #     if equiv_at_ref_PDB in ref_CGN_tf.AA2CGN.keys():
    #         iCGN = ref_CGN_tf.AA2CGN[equiv_at_ref_PDB]
    #     else:
    #         iCGN = None
    #     #print(key, top.residue(key), iCGN)
    #     out_dict[key]=iCGN
    # if keep_AA_code:
    #     return out_dict
    # else:
    #     return {int(key[1:]):val for key, val in out_dict.items()}


def _relabel_consensus(idx, input_dicts, no_key="NA"):
    labels  = [idict[idx] for idict in input_dicts]
    good_label = [ilab for ilab in labels if str(ilab).lower()!="none"]
    assert len(good_label)<=1, "There can only be one good label, but for residue %u found %s"%(idx, good_label)
    try:
        return good_label[0]
    except IndexError:
        return no_key

def csv_table2TMdefs_res_idxs(itop, keep_first_resSeq=True, complete_loops=True,
                              tablefile=None,
                              reorder_by_AA_names=False):
    # TODO pass this directly as kwargs?
    kwargs = {}
    if tablefile is not None:
        kwargs = {"tablefile": tablefile}
    segment_resSeq_dict = table2TMdefs_resSeq(**kwargs)
    resseq_list = [rr.resSeq for rr in itop.residues]
    if not keep_first_resSeq:
        raise NotImplementedError

    segment_dict = {}
    first_one=True
    for key,val in segment_resSeq_dict.items():
        print(key,val)
        res_idxs = [[ii for ii, iresSeq in enumerate(resseq_list) if iresSeq==ival][0] for ival in val]
        if not res_idxs[0]<res_idxs[1] and first_one:
            res_idxs[0]=0
            first_one = False
        segment_dict[key]=res_idxs

    if complete_loops:
        segment_dict = add_loop_definitions_to_TM_residx_dict(segment_dict)
        #for key, val in segment_dict.items():
            #print('%4s %s'%(key, val))

    if reorder_by_AA_names:
        _segment_dict = {}
        for iseg_key, (ilim, jlim) in segment_dict.items():
            for ii in _np.arange(ilim, jlim+1):
                _segment_dict[_shorten_AA(itop.residue(ii))]=iseg_key
        segment_dict = _segment_dict
    return segment_dict

def add_loop_definitions_to_TM_residx_dict(segment_dict, not_present=["ICL3"], start_with='ICL'):
    loop_idxs={"ICL":1,"ECL":1}
    loop_type=start_with
    keys_out = []
    for ii in range(1,7):
        key1, key2 = 'TM%u'%  (ii + 0), 'TM%u'%  (ii + 1)
        loop_key = '%s%s'%(loop_type, loop_idxs[loop_type])
        if loop_key in not_present:
            keys_to_append = [key1, key2]
        else:
            segment_dict[loop_key] = [segment_dict[key1][-1] + 1,
                                       segment_dict[key2][0] - 1]
            #print(loop_key, segment_dict[loop_key])
            keys_to_append = [key1, loop_key, key2]
        keys_out = keys_out+[key for key in keys_to_append if key not in keys_out]

        loop_idxs[loop_type] +=1
        if loop_type=='ICL':
            loop_type='ECL'
        elif loop_type=='ECL':
            loop_type='ICL'
        else:
            raise Exception
    out_dict = {key : segment_dict[key] for key in keys_out}
    if 'H8' in segment_dict:
        out_dict.update({'H8':segment_dict["H8"]})
    return out_dict

def table2TMdefs_resSeq(tablefile="GPCRmd_B2AR_nomenclature.xlsx",
                        modifications={"S262":"F264"},
                        reduce_to_resSeq=True):

    all_defs, names = table2BW_by_AAcode(tablefile, modifications=modifications,
                                         return_defs=True)

    # First pass
    curr_key = 'None'
    keyvals = list(all_defs.items())
    breaks = []
    for ii, (key, val) in enumerate(keyvals):
        if int(val[0]) != curr_key:
            #print(key, val)
            curr_key = int(val[0])
            breaks.append(ii)
            # print(curr_key)
            # input()

    AA_dict = {}
    for idef, ii, ff in zip(names, breaks[:-1], breaks[1:]):
        #print(idef, keyvals[ii], keyvals[ff - 1])
        AA_dict[idef]=[keyvals[ii][0], keyvals[ff-1][0]]
    #print(names[-1], keyvals[ff], keyvals[-1])
    AA_dict[names[-1]] = [keyvals[ff][0], keyvals[-1][0]]
    #print(AA_dict)

    # On dictionary: just-keep the resSeq
    if reduce_to_resSeq:
        AA_dict = {key: [''.join([ii for ii in ival if ii.isnumeric()]) for ival in val] for key, val in
                   AA_dict.items()}
        AA_dict = {key: [int(ival) for ival in val] for key, val in
                   AA_dict.items()}
    return AA_dict
