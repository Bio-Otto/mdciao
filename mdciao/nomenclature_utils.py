import mdtraj as _md
import numpy as _np
from .residue_and_atom_utils import \
    int_from_AA_code as _int_from_AA_code, \
    shorten_AA as _shorten_AA

from mdciao.list_utils import \
    in_what_fragment,\
    rangeexpand as _rangeexpand

from mdciao.fragments import \
    _print_frag

from .sequence_utils import \
    alignment_result_to_list_of_dicts as _alignment_result_to_list_of_dicts, \
    _my_bioalign

from pandas import \
    read_json as _read_json, \
    read_excel as _read_excel, \
    read_csv as _read_csv, \
    DataFrame as _DataFrame, \
    unique as _pandas_unique

from collections import defaultdict as _defdict

from os import path as _path

import requests as _requests

def table2BW_by_AAcode(tablefile,
                       keep_AA_code=True,
                       return_fragments=False,
                       ):
    r"""
    Reads an excel table and returns a dictionary AAcodes so that e.g. self.AA2BW[R131] -> '3.50'

    Parameters
    ----------
    tablefile : xlsx file or pandas dataframe
        Ballesteros-Weinstein nomenclature file in excel format, optional
    keep_AA_code : boolean, default is True
        If True then output dictionary will have key of the form "Q26" else "26".
    return_fragments : boolean, default is True
        return a dictionary of fragments keyed by BW-fragment, e.g. "TM1"

    Returns
    -------

    AA2BW : dictionary
        Dictionary with residues as key and their corresponding BW notation.

    fragments : dict (optional)
        if return_fragments=True, a dictionary containing the fragments according to the excel file
    """

    if isinstance(tablefile,str):
        df = _read_excel(tablefile, header=0)
    else:
        df = tablefile

    # TODO some overlap here with with _BW_web_lookup of BW_finder
    # figure out best practice to avoid code-repetition
    # This is the most important
    AAcode2BW = {key: str(val) for key, val in df[["AAresSeq", "BW"]].values}
    # Locate definition lines and use their indices
    fragments = _defdict(list)
    for key, AArS in df[["protein_segment", "AAresSeq"]].values:
        fragments[key].append(AArS)
    fragments = {key:val for key, val in fragments.items()}

    if keep_AA_code:
        pass
    else:
        AAcode2BW =  {int(key[1:]):val for key, val in AAcode2BW.items()}

    if return_fragments:
        return AAcode2BW, fragments
    else:
        return AAcode2BW

def PDB_finder(PDB_code, local_path='.',
               try_web_lookup=True,
               verbose=True):
    r"""
    Input a pdb-code and return an :obj:`mdtraj.Trajectory`,
    by loading a local file or optionally looking up online
     (see :obj:`md_load_rscb`)

    Note
    ----
    Since filenames are case-sensitive, e.g. 3CAP will not
    find 3cap.pdb locally, but will sucessfully be found
    online (urls are not case-sensitive), returning the
    online file instead of the local one, which can lead
    to "successfull" but wrong behaviour if the local
    file had already some modifications (strip non protein etc)

    Parameters
    ----------
    PDB_code : str
        4-letter PDB code
    local_path : str, default is "."
        What directory to look into
    try_web_lookup : bool, default is True
        If the file :obj:`ref_PDB` cannot be found locally
        as .pdb or .pdb.gz, a web lookup will be tried
    verbose

    Returns
    -------
    geom : :obj:`mdtraj.Trajectory`
    return_file : str with filename,
        Will contain an url if web_lookup was necessary
    """
    try:
        file2read = _path.join(local_path, PDB_code + '.pdb')
        _geom = _md.load(file2read)
        return_file = file2read
    except (OSError, FileNotFoundError):
        try:
            file2read = _path.join(local_path, PDB_code + '.pdb.gz')
            _geom = _md.load(file2read)
            return_file = file2read
        except (OSError, FileNotFoundError):
            if verbose:
                print("No local PDB file for %s found" % PDB_code, end="")
            if try_web_lookup:
                _geom, return_file = md_load_rscb(PDB_code,
                                                  verbose=verbose,
                                                  return_url=True)
                if verbose:
                    print("found! Continuing normally")

            else:
                raise

    return _geom, return_file

def CGN_finder(identifier,
               format='CGN_%s.txt',
               local_path='.',
               try_web_lookup=True,
               verbose=True,
               dont_fail=False,
               write_to_disk=False):
    r"""Provide a four-letter PDB code and look up (first locally, then online)
    for a file that contains the Common-Gprotein-Nomenclature (CGN)
    consesus labels and return them as a :obj:`DataFrame`. See
    https://www.mrc-lmb.cam.ac.uk/CGN/ for more info on this nomenclature
    and :obj:`_finder_writer` for what's happening under the hood


    Parameters
    ----------
    identifier : str
        Typically, a PDB code
    format : str
        A format string that turns the :obj:`identifier`
        into a filename for local lookup, in case the
        user has custom filenames, e.g. 3SN6_consensus.txt
    local_path : str
        The local path to the local consensus file
    try_web_lookup : bool, default is True
        If the local lookup fails, go online
    verbose : bool, default is True
    dont_fail : bool, default is False
        Do not raise any errors that would interrupt
        a workflow and simply return None

    Returns
    -------
    DF : :obj:`DataFrame` with the consensus nomenclature
    """
    file2read = format%identifier
    file2read = _path.join(local_path, file2read)
    local_lookup_lambda = lambda file2read : _read_csv(file2read, delimiter='\t')

    web_address = "www.mrc-lmb.cam.ac.uk"
    url = "https://%s/CGN/lookup_results/%s.txt" % (web_address, identifier)
    web_lookup_lambda = local_lookup_lambda

    return _finder_writer(file2read, local_lookup_lambda,
                          url, web_lookup_lambda,
                          try_web_lookup=try_web_lookup,
                          verbose=verbose,
                          dont_fail=dont_fail,
                          write_to_disk=write_to_disk)

def _finder_writer(full_local_path,
                   local2DF_lambda,
                   full_web_address,
                   web2DF_lambda,
                   try_web_lookup=True,
                   verbose=True,
                   dont_fail=False,
                   write_to_disk=False):
    r"""
    Try local lookup with a local lambda, then web lookup with a
    web labmda and try to return a :obj:`DataFrame`
    Parameters
    ----------
    full_local_path
    full_web_address
    local2DF_lambda
    web2DF_lambda
    try_web_lookup
    verbose
    dont_fail

    Returns
    -------
    df : DataFrame or None

    """
    try:
        return_name = full_local_path
        _DF = local2DF_lambda(full_local_path)
    except FileNotFoundError as e:
        _DF = e
        if verbose:
            print("No local file %s found" % full_local_path, end="")
        if try_web_lookup:
            return_name = full_web_address
            if verbose:
                print(", checking online in\n%s ..." % full_web_address, end="")
            try:
                _DF = web2DF_lambda(full_web_address)
                if verbose:
                    print("done without 404, continuing.")
            except Exception as e:
                print('Error getting or processing the web lookup:', e)
                _DF = e

    if isinstance(_DF, _DataFrame):
        if write_to_disk:
            if _path.exists(full_local_path):
                raise FileExistsError("Cannot overwrite exisiting file %s" % full_local_path)
            if _path.splitext(full_local_path)[-1]==".xlsx":
                _DF.to_excel(full_local_path)
            else:
                # see https://github.com/pandas-dev/pandas/issues/10415
                with open(full_local_path,"w") as f:
                    f.write(_DF.to_string(index=False,header=True))

            print("wrote %s for future use" % full_local_path)
        return _DF, return_name
    else:
        if dont_fail:
            return None, return_name
        else:
            raise _DF


def BW_finder(uniprot_name,
              format = "%s.xlsx",
              local_path=".",
              try_web_lookup=True,
              verbose=True,
              dont_fail=False,
              write_to_disk=False):
    xlsxname = format % uniprot_name
    fullpath = _path.join(local_path, xlsxname)

    GPCRmd = "https://gpcrdb.org/services/residues/extended"
    url = "%s/%s" % (GPCRmd, uniprot_name)

    local_lookup_lambda = lambda fullpath : _read_excel(fullpath,
                                                        usecols=lambda x : x.lower()!="unnamed: 0",
                                                        converters={"BW": str}).replace({_np.nan: None})
    web_looukup_lambda = lambda url : _BW_web_lookup(url, verbose=verbose)

    return _finder_writer(fullpath, local_lookup_lambda,
                          url, web_looukup_lambda,
                          try_web_lookup=try_web_lookup,
                          verbose=verbose,
                          dont_fail=dont_fail,
                          write_to_disk=write_to_disk)

def _BW_web_lookup(url, verbose=True):
    r"""
    Lookup this url for a BW-notation
    return a ValueError if the lookup retuns an empty json
    Parameters
    ----------
    url
    verbose

    Returns
    -------

    """
    uniprot_name = url.split("/")[-1]
    a = _requests.get(url)
    if verbose:
        print("done!")
    if a.text == '[]':
        DFout = ValueError('Contacted %s url sucessfully (no 404),\n'
                           'but Uniprot name %s yields nothing' % (url, uniprot_name))
    else:
        df = _read_json(a.text)
        mydict = df.T.to_dict()
        for key, val in mydict.items():
            try:
                for idict in val["alternative_generic_numbers"]:
                    # print(key, idict["scheme"], idict["label"])
                    val[idict["scheme"]] = idict["label"]
                val.pop("alternative_generic_numbers")
                val["AAresSeq"] = '%s%s' % (val["amino_acid"], val["sequence_number"])
            except IndexError:
                pass
        DFout = _DataFrame.from_dict(mydict, orient="index").replace({_np.nan: None})
        DFout = DFout[["protein_segment", "AAresSeq",
                       "BW",
                       "GPCRdb(A)",
                       "display_generic_number"]]

    return DFout

#todo document and refactor to better place?
def md_load_rscb(PDB,
                 web_address = "https://files.rcsb.org/download",
                 verbose=False,
                 return_url=False):
    r"""
    Input a PDB code get an :obj:`mdtraj.Trajectory` object

    Parameters
    ----------
    PDB : str
        4-letter PDB code
    web_address: str, default is "https://files.rcsb.org/download"
    verbose : bool, default is False
        Be versose
    return_url : bool, default is False
        also Return the actual url that was checked

    Returns
    -------
    traj, url
    """
    url = '%s/%s.pdb' % (web_address, PDB)
    if verbose:
        print(", checking online in \n%s ..." % url, end="")
    igeom = _md.load_pdb(url)
    if return_url:
        return igeom, url
    else:
        return igeom

class LabelerConsensus(object):
    """
    Class to manage consensus notations like
    * Ballesteros-Weinstein (BW)
    * Common-Gprotein-nomenclature

    The consensus labels are abbreviated to 'conlab' throughout

    """
    def __init__(self, ref_PDB=None, **PDB_finder_kwargs):
        r"""

        Parameters
        ----------
        tablefile: str, default is 'GPCRmd_B2AR_nomenclature'
            The PDB four letter code that will be used for CGN purposes
        ref_path: str,default is '.'
            The local path where the needed files are

        try_web_lookup: bool, default is True
            If the local files are not found, try automatically a web lookup at
             * www.mrc-lmb.cam.ac.uk (for CGN)
             * rcsb.org (for the PDB)

        """
        self._geom_PDB = None
        self._ref_top = None
        self._ref_PDB = ref_PDB
        if ref_PDB is not None:
            self._geom_PDB, self._PDB_file = PDB_finder(ref_PDB,
                                                        **PDB_finder_kwargs,
                                                        )
        self._conlab2AA = {val: key for key, val in self.AA2conlab.items()}

        self._fragment_names = list(self.fragments.keys())
        self._fragments_as_conlabs = {key: [self.AA2conlab[AA] for AA in val]
                                      for key, val in self.fragments.items()}

    @property
    def ref_PDB(self):
        r""" PDB code used for instantiation"""
        return self._ref_PDB

    @property
    def geom(self):
        r""" :obj:`mdtraj.Trajectory` with with what was found
        (locally or online) using :obj:`ref_PDB`"""
        return self._geom_PDB

    @property
    def top(self):
        r""" :obj:`mdtraj.Topology` with with what was found
                (locally or online) using :obj:`ref_PDB`"""
        return self._geom_PDB.top

    @property
    def conlab2AA(self):
        r""" Dictionary with consensus labels as keys, so that e.g.
            * self.conlab2AA["3.50"] -> 'R131' or
            * self.conlab2AA["G.hfs2.2"] -> 'R201' """
        return self._conlab2AA

    @property
    def AA2conlab(self):
        r""" Dictionary with AA-codes as keys, so that e.g.
            * self.AA2BW["R131"] -> '3.50'
            * self.conlab2AA["R201"] -> "G.hfs2.2" """


        return self._AA2conlab

    @property
    def fragment_names(self):
        r"""Name of the fragments according to the consensus labels

        TODO OR NOT? Check!"""
        return self._fragment_names

    @property
    def fragments(self):
        r""" Dictionary of fragments keyed with fragment names
        and valued with the residue names (AAresSeq) in that fragment.
        """

        return self._fragments

    @property
    def fragments_as_conlabs(self):
        r""" Dictionary of fragments keyed with fragment names
        and valued with the consensus labels in that fragment

        Returns
        -------
        """
        return self._fragments_as_conlabs

    @property
    def dataframe(self):
        return self._dataframe

    @property
    def tablefile(self):
        r""" The file used to instantiate this transformer"""
        return self._tablefile

    def conlab2residx(self,top,
                      restrict_to_residxs=None,
                      map=None,
                      keep_consensus=False):
        r"""
        Returns a dictionary keyed by consensus labels and valued
        by residue indices of the input topology in :obj:`top`.

        The default behaviour is to internally align :obj:`top`
        with :obj:`self.top` on the fly using :obj:`_top2consensus_map`


        Note
        ----
        This method is able to work with a new topology every
        time, performing a sequence alginment every call.
        The intention is to instantiate a
        :obj:`LabelerConsensus` jus one time and use it with as
        many topologies as you like without changing any attribute
        of :obj:`self`.

        HOWEVER, if you know what you are doing, you can provide a
        list of consensus labels yourself using :obj:`map`. Then,
        this method is nothing but a table lookup (almost)

        Warning
        -------
        No checks are performed to see if the input of :obj:`map`
        actually matches the residues of :obj:`top in any way,
        so that the output can be rubbish and go unnoticed.


        Parameters
        ----------
        top : :obj:`mdtraj.Topology`
        restrict_to_residxs : iterable of indices, default is None
            Align using only these indices, see :obj:`_top2consensus_map`
            for more info. Has no effect if :obj:`map` is None
        map : list, default is None
            A pre-computed residx2consensuslabel map, i.e. the
            output of a previous, external call to :obj:`_top2consensus_map`
            If it contains duplicates, it is a malformed list.
            See the note above for more info

        keep_consensus : bool, default is False
            Wheater to autofill consensus labels on the fly
        Returns
        -------
        dict : keyed by consensus labels and valued with residue idxs???
        """
        if map is None:
            map = _top2consensus_map(self.AA2conlab, top,
                                     restrict_to_residxs=restrict_to_residxs,
                                     keep_consensus=keep_consensus)
        out_dict = {}
        for ii,imap in enumerate(map):
            if imap is not None:
                if imap in out_dict.keys():
                    raise ValueError("Entries %u and %u of the map, "
                                     "i.e. residues %s and %s of the input topology "
                                     "both have the same label %s.\n"
                                     "This method cannot work with a map like this!"%(out_dict[imap], ii,
                                                                                     top.residue(out_dict[imap]),
                                                                                     top.residue(ii),
                                                                                     imap))
                else:
                    out_dict[imap]=ii
        return out_dict

    def top2map(self, top, restrict_to_residxs=None, fill_gaps=False,
                verbose=False):
        r""" Align the sequence of :obj:`top` to the sequence used
        to initialize this :obj:`LabelerConsensus` and return a
        list list of consenus labels for each residue in :obj:`top`.

        The if a consensus label is returned as None it means one
        of two things:
            * this position was sucessfully aligned with a
             match but the data used to initialize this
             :obj:`ConsensusLabeler` did not contain a label

            * this position has a label in the original data
            but the sequence alignment is not matched (e.g.,
            bc of a point mutation)

        A heuristic to "autofill" the second case can be
        turned on using :obj:`fill_gaps`, see :obj:`_fill_CGN_gaps`
        for more info

        Note
        ----
        This method simply wraps around :obj:`_top2consensus_map`
        using the object's own data, see the doc on that method
        for more info.

        Parameters
        ----------
        top :
            :py:class:`mdtraj.Topology` object
        restrict_to_residxs: iterable of integers, default is None
            Use only these residues for alignment and labelling options.
            The return list will still be of length=top.n_residues
        fill_gaps: boolean, default is False
            Try to fill gaps in the consensus nomenclature by calling
            :obj:`_fill_CGN_gaps`

        Returns
        -------
        map : list of len = top.n_residues with the consensus labels
        """

        return _top2consensus_map(self.AA2conlab, top,
                                  restrict_to_residxs=restrict_to_residxs,
                                  keep_consensus=fill_gaps,
                                  verbose=verbose,
                                  )

    def top2defs(self, top, map=None,
                 return_defs=False,
                 fragments=None,
                 fill_gaps=False,
                 ):
        r"""
        Prints the definitions of subdomains that the
        consenus nomenclature contains and map it out
        in terms of residue indices of the input :obj:`top`

        Does not return anything unless explicitly asked to.

        Parameters
        ----------
        top:
            :py:class:`mdtraj.Topology` object
        map:  list, default is None
            The user can parse an exisiting "top2map" map, otherwise this
            method will generate one on the fly. It is recommended (but
            not needed) to pre-compute and pass such a map cases where:
            * the user is sure that the map is the same every time
            the method gets called.
            * the on-the-fly creation of the map slows down the workflow
            * in critical cases when alignment is poor and
            naming errors are likely
        return_defs: boolean, default is False
            If True, apart from printing the definitions,
            they are returned as a dictionary
        fragments: iterable of integers, default is None
            The user can parse an existing list of fragment-definitions
            (via residue idxs) to check if newly found, consensus
            definitions (:obj:`defs`) clash with the input in :obj:`fragments`.
            *Clash* means that the consensus definitions span over (=cross over?)
            the definitions in :obj:`fragments`.

            An interactive prompt will ask the user which fragments to
            keep

            Example
            -------
            In other words, the consensus definitions cannot
            contain more than one of the :obj:`fragments`:
            * defs["TM6"] = [1,2,3,4] and :obj:`fragments`=[[0,1,2,3,4,6], [7,8,9]]
            is not a clash, bc TM6 is contained in fragments[0]
            * defs["TM6"] = [0,1,2,3] and :obj:`fragments`=[[0,1],[2,3,4,5,6,7,8]]
            is a clash. In this case the user will be prompted to choose
            which fragments to keep in "TM6" (0 or 1). The answer cannot be both.

        fill_gaps: boolean, default is False
            Try to fill gaps in the consensus nomenclature by calling
            :obj:`_fill_CGN_gaps`. It has no effect if the user inputs
            the map

        Returns
        -------
        defs : dictionary (if return_defs is True)
            Dictionary with subdomain names as keys and lists of indices as values
        """

        if map is None:
            print("creating a temporary map, this is dangerous")
            map = self.top2map(top, fill_gaps=fill_gaps, verbose=False)

        conlab2residx = self.conlab2residx(top, map=map)
        defs = _defdict(list)
        for key, ifrag in self.fragments_as_conlabs.items():
            for iBW in ifrag:
                if iBW in conlab2residx.keys():
                    defs[key].append(conlab2residx[iBW])
        defs = {key:val for key,val in defs.items()}
        new_defs = {}
        for ii, (key, val) in enumerate(defs.items()):
            if fragments is not None:
                # TODO this should be its own method
                # Get the fragment idxs of all residues in this fragment
                ifrags = [in_what_fragment(idx, fragments) for idx in val]
                # This only happens if more than one fragment is present
                frag_cands = [ifrag for ifrag in _pandas_unique(ifrags) if ifrag is not None]
                if len(frag_cands)>1:
                    _print_frag(key, top, val, fragment_desc='')
                    print("The range %s to %s contains more than one fragment:" % (map[val[0]], map[val[-1]]))
                    #todo AVOID ASKING THE USER
                    for jj in frag_cands:
                        istr = _print_frag(jj,top, fragments[jj], fragment_desc=" input fragment",
                                           return_string=True)
                        #print(istr)
                        n_in_fragment = len(_np.intersect1d(val,fragments[jj]))
                        if n_in_fragment<len(fragments[jj]):
                            istr += "%u residues outside %s"%(len(fragments[jj])-n_in_fragment,key)
                        print(istr)
                    answr = input("Input what fragment idxs to include into %s  (fmt = 1 or 1-4, or 1,3):"%key)
                    answr = _rangeexpand(answr)
                    assert all([idx in ifrags for idx in answr])
                    tokeep = _np.hstack([idx for ii, idx in enumerate(val) if ifrags[ii] in answr]).tolist()
                    if len(tokeep)>=len(ifrags):
                        raise ValueError("Cannot keep these fragments %s!"%(str(answr)))
                    new_defs[key] = tokeep

        for key, val in new_defs.items():
            defs[key]=val

        for ii, (key, val) in enumerate(defs.items()):
            istr = _print_frag(key, top, val, fragment_desc='', return_string=True)
            print(istr)
        if return_defs:
            return {key:val for key, val in defs.items()}


class LabelerCGN(LabelerConsensus):
    """
    Class to abstract, handle, and use common-Gprotein-nomenclature.
    See https://www.mrc-lmb.cam.ac.uk/CGN/faq.html for more info.
    """

    def __init__(self, ref_PDB,
                 local_path='.',
                 try_web_lookup=True,
                 verbose=True):
        r"""

        Parameters
        ----------
        ref_PDB: str
            The PDB four letter code that will be used for CGN purposes
        local_path: str, default is '.'
            The local path where these files exist, if they exist
            * 3SN6_CGN.txt (pre-downloaded CGN-type file)
            * 3SN6.pdb     (pre-downloaded pdb)
        try_web_lookup: bool, default is True
            If the local files are not found, try automatically a web lookup at
            * www.mrc-lmb.cam.ac.uk (for CGN)
            * rcsb.org (for the PDB)
        """

        self._dataframe, self._tablefile = CGN_finder(ref_PDB,
                                                      local_path=local_path,
                                                      try_web_lookup=try_web_lookup,
                                                      verbose=verbose)

        self._AA2conlab = {key: self._dataframe[self._dataframe[ref_PDB] == key]["CGN"].to_list()[0]
                           for key in self._dataframe[ref_PDB].to_list()}

        self._fragments = _defdict(list)
        for ires, key in self.AA2conlab.items():
            try:
                new_key = '.'.join(key.split(".")[:-1])
            except:
                print(key)
            #print(key,new_key)
            self._fragments[new_key].append(ires)
        #print(self.fragments)
        LabelerConsensus.__init__(self, ref_PDB=ref_PDB,
                                  local_path=local_path,
                                  try_web_lookup=try_web_lookup,
                                  verbose=verbose)

class LabelerBW(LabelerConsensus):
    """
    Class to manage Ballesteros-Weinstein notation

    """
    def __init__(self, uniprot_name,
                 ref_PDB=None,
                 local_path=".",
                 format="%s.xlsx",
                 verbose=True,
                 try_web_lookup=True,
                 #todo write to disk should be moved to the superclass at some point
                 write_to_disk=False):

        # TODO now that the finder call is the same we could
        # avoid cde repetition here
        self._dataframe, self._tablefile = BW_finder(uniprot_name,
                                            format=format,
                                            local_path=local_path,
                                            try_web_lookup=try_web_lookup,
                                            verbose=verbose,
                                            write_to_disk=write_to_disk
                                       )

        self._AA2conlab, self._fragments = table2BW_by_AAcode(self.dataframe, return_fragments=True)
        # TODO can we do this using super?
        LabelerConsensus.__init__(self, ref_PDB,
                                  local_path=local_path,
                                  try_web_lookup=try_web_lookup,
                                  verbose=verbose)

def guess_missing_BWs(input_BW_dict,top, restrict_to_residxs=None, keep_keys=False):
    """
    Estimates the BW for residues which are not present in the nomenclature file.

    Parameters
    ----------
    input_BW_dict : dictionary
        BW dictionary with residue names as the key and their corresponding BW notation
    top : :py:class:`mdtraj.Topology`
    restrict_to_residxs: list, optional
        residue indexes for which the BW needs to be estimated. (Default value is None, which means all).

    Returns
    -------
    BW : list
        list of len=top.n_residues including estimated missing BW-names,
        it also retains all the values from the input dictionary.

    """

    if restrict_to_residxs is None:
        restrict_to_residxs = [residue.index for residue in top.residues]

    #TODO keep this until we are sure there are no consquences
    out_list = [None for __ in top.residues]
    for rr in restrict_to_residxs:
        residue = top.residue(rr)
        key = '%s%s'%(residue.code,residue.resSeq)
        try:
            (key, input_BW_dict[key])
            #print(key, input_BW_dict[key])
            out_list[residue.index] = input_BW_dict[key]
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
                out_list[residue.index] = new_guessed_val
                #print(key, new_guessed_val, residue.index, residue.index in restrict_to_residxs)
            else:
                pass
                #new_guessed_val = None

            # print("closest",closest_BW_key,closest_BW, key, new_guessed_val )

    #input_BW_dict.update(guessed_BWs)

    if keep_keys:
        guessed_BWs = {}
        used_keys = []
        for res_idx, val in enumerate(out_list):
            new_key = _shorten_AA(top.residue(res_idx))
            if new_key in input_BW_dict.keys():
                assert val==input_BW_dict[new_key],"This should not have happened %s %s %s"%(val, new_key, input_BW_dict[new_key])
            assert new_key not in used_keys
            guessed_BWs[new_key]=val
            used_keys.append(new_key)
        return guessed_BWs
    else:
        return out_list

def _top2consensus_map(consensus_dict, top,
                       restrict_to_residxs=None,
                       keep_consensus=False,
                       verbose=False,
                       ):
    r"""
    Align the sequence of :obj:`top` to consensus
    dictionary's sequence (typically in :obj:`ContactLabeler.AA2conlab`))
    and return a list of consensus numbering for each residue
     in :obj:`top`.

    For the alignment details see :obj:`my_Bioalign`

    If no consensus numbering
    is found after the alignment, the residues entry will be None

    Parameters
    ----------
    consensus_dict : dictionary
        AA-codes as keys and nomenclature as values, e.g. AA2CGN["K25"] -> G.HN.42
    top :
        :py:class:`mdtraj.Topology` object
    restrict_to_residxs: iterable of integers, default is None
        Use only these residues for alignment and labelling purposes
        Helps "guide" the alignment method. E.g., one might be
        passing an Ballesteros-Weinstein in :obj:`consensus_dict` but
        the topology also contains the whole G-protein. If available,
        one can pass here the indices of residues of the receptor
    keep_consensus : boolean default is False
        Even if there is a consensus mismatch with the sequence of the input
        :obj:`consensus_dict`, try to relabel automagically, s.t.
        * ['G.H5.25', 'G.H5.26', None, 'G.H.28']
        will be grouped relabeled as
        * ['G.H5.25', 'G.H5.26', 'G.H.27', 'G.H.28']

    verbose: boolean, default is False
        be verbose

    Returns
    -------
    map : list
        list of length top.n_residues containing consensus labels
    """

    if restrict_to_residxs is None:
        restrict_to_residxs = [residue.index for residue in top.residues]
    seq = ''.join([_shorten_AA(top.residue(ii), keep_index=False, substitute_fail='X') for ii in restrict_to_residxs])
    from mdciao.residue_and_atom_utils import name_from_AA as _name_from_AA
    seq_consensus= ''.join([_name_from_AA(key) for key in consensus_dict.keys()])
    alignment = _alignment_result_to_list_of_dicts(_my_bioalign(seq, seq_consensus)[0],
                                                   top,
                                                   restrict_to_residxs,
                                                   [_int_from_AA_code(key) for key in consensus_dict],
                                                   verbose=verbose
                                                   )
    alignment = _DataFrame(alignment)
    alignment = alignment[alignment["match"] == True]
    out_list = [None for __ in top.residues]
    for idx, resSeq, AA in alignment[["idx_0","idx_1", "AA_1"]].values:
        out_list[int(idx)]=consensus_dict[AA + str(resSeq)]

    if keep_consensus:
        out_list = _fill_CGN_gaps(out_list, top, verbose=True)
    return out_list

def _fill_CGN_gaps(consensus_list, top, verbose=False):
    r""" Try to fill CGN consensus nomenclature gaps based on adjacent labels

    The idea is to fill gaps of the sort:
     * ['G.H5.25', 'G.H5.26', None, 'G.H.28']
      to
     * ['G.H5.25', 'G.H5.26', 'G.H.27', 'G.H.28']

    The size of the gap is variable, it just has to match the length of
    the consensus labels, i.e. 28-26=1 which is the number of "None" the
    input list had

    Parameters
    ----------
    consensus_list: list
        List of length top.n_residues with the original consensus labels
        Supossedly, it contains some "None" entries inside sub-domains
    top :
        :py:class:`mdtraj.Topology` object
    verbose : boolean, default is False

    Returns
    -------
    consensus_list: list
        The same as the input :obj:`consensus_list` with guessed missing entries
    """

    defs = _map2defs(consensus_list)
    #todo decrease verbosity
    for key, val in defs.items():

        # Identify problem cases
        if len(val)!=val[-1]-val[0]+1:
            if verbose:
                print(key)

            # Initialize residue_idxs_wo_consensus_labels control variables
            offset = int(consensus_list[val[0]].split(".")[-1])
            consensus_kept=True
            suggestions = []
            residue_idxs_wo_consensus_labels=[]

            # Check whether we can predict the consensus labels correctly
            for ii in _np.arange(val[0],val[-1]+1):
                suggestions.append('%s.%u'%(key,offset))
                if consensus_list[ii] is None:
                    residue_idxs_wo_consensus_labels.append(ii)
                else: # meaning, we have a consensus label, check it against suggestion
                    consensus_kept *= suggestions[-1]==consensus_list[ii]
                if verbose:
                    print('%6u %8s %10s %10s %s'%(ii, top.residue(ii),consensus_list[ii], suggestions[-1], consensus_kept))
                offset += 1
            if verbose:
                print()
            if consensus_kept:
                if verbose:
                    print("The consensus was kept, I am relabelling these:")
                for idx, res_idx in enumerate(_np.arange(val[0],val[-1]+1)):
                    if res_idx in residue_idxs_wo_consensus_labels:
                        consensus_list[res_idx] = suggestions[idx]
                        if verbose:
                            print(suggestions[idx])
            else:
                if verbose:
                    print("Consensus wasn't kept. Nothing done!")
            if verbose:
                print()
    return consensus_list


def _fill_BW_gaps(consensus_list, top, verbose=False):
    r""" Try to fill BW consensus nomenclature gaps based on adjacent labels

    The idea is to fill gaps of the sort:
     * ['1.25', '1.26', None, '1.28']
      to
     * ['1.25', '1.26', '1.27, '1.28']

    The size of the gap is variable, it just has to match the length of
    the consensus labels, i.e. 28-26=1 which is the number of "None" the
    input list had

    Parameters
    ----------
    consensus_list: list
        List of length top.n_residues with the original consensus labels
        Supossedly, it contains some "None" entries inside sub-domains
    top :
        :py:class:`mdtraj.Topology` object
    verbose : boolean, default is False

    Returns
    -------
    consensus_list: list
        The same as the input :obj:`consensus_list` with guessed missing entries
    """

    defs = _map2defs(consensus_list)
    for key, val in defs.items():

        # Identify problem cases
        if len(val)!=val[-1]-val[0]+1:
            if verbose:
                print(key)

            # Initialize residue_idxs_wo_consensus_labels control variables
            offset = int(consensus_list[val[0]].split(".")[-1])
            consensus_kept=True
            suggestions = []
            residue_idxs_wo_consensus_labels=[]

            # Check whether we can predict the consensus labels correctly
            for ii in _np.arange(val[0],val[-1]+1):
                suggestions.append('%s.%u'%(key,offset))
                if consensus_list[ii] is None:
                    residue_idxs_wo_consensus_labels.append(ii)
                else: # meaning, we have a consensus label, check it against suggestion
                    consensus_kept *= suggestions[-1]==consensus_list[ii]
                if verbose:
                    print(ii, top.residue(ii),consensus_list[ii], suggestions[-1], consensus_kept)
                offset += 1
            if verbose:
                print()
            if consensus_kept:
                if verbose:
                    print("The consensus was kept, I am relabelling these:")
                for idx, res_idx in enumerate(_np.arange(val[0],val[-1]+1)):
                    if res_idx in residue_idxs_wo_consensus_labels:
                        consensus_list[res_idx] = suggestions[idx]
                        if verbose:
                            print(suggestions[idx])
            if verbose:
                print()
    return consensus_list


def top2CGN_by_AAcode(top, ref_CGN_tf,
                      restrict_to_residxs=None,
                      verbose=False):
    """
    Returns a dictionary of CGN (Common G-protein Nomenclature) labelling for each residue.
    The keys are zero-indexed residue indices

    TODO if the length of the dictionary is always top.n_residues, consider simply returning a list

    Parameters
    ----------
    top :
        :py:class:`mdtraj.Topology` object
    ref_CGN_tf :
        :class:`LabelerCGN` object
    restrict_to_residxs: list, optional, default is None
        residue indexes for which the CGN needs to be found out. Default behaviour is for all
        residues in the :obj:`top`.

    Returns
    -------
    CGN_list : list
        list of length obj:`top.n_residues` containing the CGN numbering (if found), None otherwise

    """

    if restrict_to_residxs is None:
        restrict_to_residxs = [residue.index for residue in top.residues]


    seq = ''.join([str(top.residue(ii).code).replace("None", "X") for ii in restrict_to_residxs])


    # As complicated as this seems, it's just cosmetics for the alignment dictionaries
    AA_code_seq_0_key = "AA_input"
    full_resname_seq_0_key = 'resname_input'
    resSeq_seq_0_key = "resSeq_input"
    AA_code_seq_1_key = 'AA_ref(%s)' % ref_CGN_tf.ref_PDB
    idx_seq_1_key = 'resSeq_ref(%s)' % ref_CGN_tf.ref_PDB
    idx_seq_0_key = 'idx_input'
    for alignmt in _my_bioalign(seq, ref_CGN_tf.seq)[:1]:
        #TODO this fucntion has been changed and this transformer will not work anymore
        # major bug (still?)

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
            from .sequence_utils import print_verbose_dataframe
            print_verbose_dataframe(pd.DataFrame.from_dict(list_of_alignment_dicts))
            input("This is the alignment. Hit enter to continue")

        # TODO learn to tho dis with pandas
        list_out = [None for __ in top.residues]
        for idict in list_of_alignment_dicts:
            if idict["match"]==True:
                res_idx_input = restrict_to_residxs[idict[idx_seq_0_key]]
                match_name = '%s%s'%(idict[AA_code_seq_1_key],idict[idx_seq_1_key])
                iCGN = ref_CGN_tf.AA2CGN[match_name]
                if verbose:
                    print(res_idx_input,"res_idx_input",match_name, iCGN)
                list_out[res_idx_input]=iCGN

        if verbose:
            for idx, iCGN in enumerate(list_out):
                print(idx, iCGN, top.residue(idx))
            input("This is the actual return value. Hit enter to continue")
    return list_out

def _relabel_consensus(idx, consensus_dicts, no_key="NA"):
    """
    Assigns labels based on the residue index
    Parameters
    ----------
    idx : int
        index for which the relabeling is needed
    consensus_dicts : list
        each item in the list should be a dictionary. The keys of each dictionary should be the residue idxs,
        and the corresponding value should be the label.
    no_key : str
        output message if there is no label for the residue idx in any of the dictionaries.

    Returns
    -------
    string
        label of the residue idx if present else "NA"

    """
    labels  = [idict[idx] for idict in consensus_dicts]
    good_label = [ilab for ilab in labels if str(ilab).lower()!="none"]
    assert len(good_label)<=1, "There can only be one good label, but for residue %u found %s"%(idx, good_label)
    try:
        return good_label[0]
    except IndexError:
        return no_key

def csv_table2TMdefs_res_idxs(itop, keep_first_resSeq=True, complete_loops=True,
                              tablefile=None,
                              reorder_by_AA_names=False):
    """

    Parameters
    ----------
    itop
    keep_first_resSeq
    complete_loops
    tablefile
    reorder_by_AA_names

    Returns
    -------

    """
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
    """
    Adds the intra- and extracellular loop definitions on the existing TM residue index dictionary.
    Example - If there are TM1-TM7 definitions with there corresponding indexes then the output will be-
        *ICL1 is added between TM1 and TM2
        *ECL1 is added between TM2 and TM3
        *ICL2 is added between TM3 and TM4
        *ECL2 is added between TM4 and TM5
        *ECL3 is added between TM6 and TM7

    Note- "ICL3" is not being explicitly added

    Parameters
    ----------
    segment_dict : dict
        TM definition as the keys and the residue idx list as values of the dictionary
    not_present : list
        definitions which should not be added to the existing TM definitions
    start_with : str
        only the string part the first definition that should be added to the existing TM definitions

    Returns
    -------
    dict
    updated dictionary with the newly added loop definitions as keys and the corresponding residue index list,
    as values. The original key-value pairs of the TM definition remains intact.

    """
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
                        #modifications={"S262":"F264"},
                        reduce_to_resSeq=True):
    """
    Returns a dictionary with the TM number as key and their corresponding amino acid resSeq range as values,
    based on the BW nomenclature excel file

    Parameters
    ----------
    tablefile : xlsx file
        GPCRmd_B2AR nomenclature file in excel format, optional
    reduce_to_resSeq

    Returns
    -------
    dictionary
    with the TM definitions as the keys and the first and the last amino acid resSeq number as values.
    example- if amino acid Q26 corresponds to TM1, the output will be {'TM1' : [26, 26]}

    """

    all_defs, names = table2BW_by_AAcode(tablefile,
                                         #modifications=modifications,
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
        #print(idef, keyvals[ii], keyvals[pattern - 1])
        AA_dict[idef]=[keyvals[ii][0], keyvals[ff-1][0]]
    #print(names[-1], keyvals[pattern], keyvals[-1])
    AA_dict[names[-1]] = [keyvals[ff][0], keyvals[-1][0]]
    #print(AA_dict)

    # On dictionary: just-keep the resSeq
    if reduce_to_resSeq:
        AA_dict = {key: [''.join([ii for ii in ival if ii.isnumeric()]) for ival in val] for key, val in
                   AA_dict.items()}
        AA_dict = {key: [int(ival) for ival in val] for key, val in
                   AA_dict.items()}
    return AA_dict

def _guess_nomenclature_fragments(CLtf, top, fragments,
                                  min_hit_rate=.6,
                                  verbose=False):
    """

    Parameters
    ----------
    CLtf:
        :class:`LabelerConsensus` object
    top:
        :py:class:`mdtraj.Topology` object
    fragments :
    min_hit_rate: float, default is .75
        return only fragments with hit rates higher than this
    verbose: boolean
        be verbose

    Returns
    -------
    guess: list
        indices of the fragments with higher hit-rate than :obj:`cutoff`

    """
    aligned_BWs = CLtf.top2map(top, fill_gaps=False)
    #for ii, iBW in enumerate(aligned_BWs):
    #    print(ii, iBW, top.residue(ii))
    hits, guess = [], []
    for ii, ifrag in enumerate(fragments):
        hit = [aligned_BWs[jj] for jj in ifrag if aligned_BWs[jj] is not None]
        if len(hit)/len(ifrag)>=min_hit_rate:
            guess.append(ii)
        if verbose:
            print(ii, len(hit)/len(ifrag))
        hits.append(hit)
    return guess

def _map2defs(cons_list):
    r"""
    Regroup a list of consensus labels into their subdomains. The indices of the list
    are interpreted as residue indices in the topology used to generate :obj:`cons_list`
    in the first place, e.g. by using :obj:`nomenclature_utils._top2consensus_map`

    Note:
    -----
     The method will guess automagically whether this is a CGN or BW label by
     checking the type of the first character (numeric is BW, 3.50, alpha is CGN, G.H5.1)

    Parameters
    ----------
    cons_list: list
        Contains consensus labels for a given topology, s.t. indices of
        the list map to residue indices of a given topology, s.t.
        cons_list[10] has the consensus label of top.residue(10)

    Returns
    -------
    map : dictionary
        dictionary with subdomains as keys and lists of consesus labels as values
    """
    defs = _defdict(list)
    for ii, key in enumerate(cons_list):
        if key is not None:
            if key[0].isnumeric(): # it means it is BW
                new_key =key.split(".")[0]
            elif key[0].isalpha(): # it means it CGN
                new_key = '.'.join(key.split(".")[:-1])
            else:
                raise Exception(new_key)
            defs[new_key].append(ii)

    return {key: _np.array(val) for key, val in defs.items()}

def order_frags(fragment_names, consensus_labels):
    from natsort import natsorted
    labs_out = []
    for ifrag in fragment_names:
        if 'CL' in ifrag:
            toappend = natsorted([ilab for ilab in consensus_labels if ilab.endswith(ifrag)])
        else:
            toappend = natsorted([ilab for ilab in consensus_labels if ilab.startswith(ifrag)])
        if len(toappend) > 0:
            labs_out.extend(toappend)
    for ilab in consensus_labels:
        if ilab not in labs_out:
            labs_out.append(ilab)
    return labs_out

def order_BW(labels):
    return order_frags("1 12 2 23 3 34 ICL2 4 45 5 56 ICL3 6 67 7 78 8".split(), labels)
def order_CGN(labels):
    return order_frags(_CGN_fragments,labels)

_CGN_fragments = ['G.HN',
                 'G.hns1',
                 'G.S1',
                 'G.s1h1',
                 'G.H1',
                 'H.HA',
                 'H.hahb',
                 'H.HB',
                 'H.hbhc',
                 'H.HC',
                 'H.hchd',
                 'H.HD',
                 'H.hdhe',
                 'H.HE',
                 'H.hehf',
                 'H.HF',
                 'G.hfs2',
                 'G.S2',
                 'G.s2s3',
                 'G.S3',
                 'G.s3h2',
                 'G.H2',
                 'G.h2s4',
                 'G.S4',
                 'G.s4h3',
                 'G.H3',
                 'G.h3s5',
                 'G.S5',
                 'G.s5hg',
                 'G.HG',
                 'G.hgh4',
                 'G.H4',
                 'G.h4s6',
                 'G.S6',
                 'G.s6h5',
                 'G.H5']