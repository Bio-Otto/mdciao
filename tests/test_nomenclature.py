import unittest
import mdtraj as md
import numpy as _np
from os import path
from tempfile import TemporaryDirectory as _TDir
from urllib.error import HTTPError
from shutil import copy

import pytest
from mdciao import nomenclature_utils
#TODO make these imports cleaner
from mdciao.nomenclature_utils import *
from filenames import filenames

from mdciao.fragments import get_fragments

import mock

from pandas import DataFrame

test_filenames = filenames()

class Test_md_load_rscb(unittest.TestCase):

    def test_works(self):
        geom = nomenclature_utils.md_load_rscb("3CAP",
                                               verbose=True,
                                                    )
        assert isinstance(geom, md.Trajectory)
    def test_works_return_url(self):
        geom, url = nomenclature_utils.md_load_rscb("3CAP",
                           #verbose=True,
                           return_url=True
                                                    )
        assert isinstance(geom, md.Trajectory)
        assert isinstance(url, str)
        assert "http" in url

class Test_PDB_finder(unittest.TestCase):

    def test_works_locally(self):
        geom, filename = nomenclature_utils.PDB_finder("file_for_test",
                                                       local_path=test_filenames.test_data_path,
                                                       try_web_lookup=False)
        assert isinstance(geom, md.Trajectory)
        assert isinstance(filename, str)

    def test_works_locally_pdbgz(self):
        geom, filename = nomenclature_utils.PDB_finder("3cap",
                                                       local_path=test_filenames.test_data_path,
                                                       try_web_lookup=False)
        assert isinstance(geom, md.Trajectory)
        assert isinstance(filename, str)

    def test_works_online(self):
        geom, filename = nomenclature_utils.PDB_finder("3SN6")

        assert isinstance(geom, md.Trajectory)
        assert isinstance(filename, str)
        assert "http" in filename

    def test_fails_bc_no_online_access(self):
        with pytest.raises((OSError,FileNotFoundError)):
            nomenclature_utils.PDB_finder("3SN6",
                                          try_web_lookup=False)

class Test_CGN_finder(unittest.TestCase):

    def test_works_locally(self):
        df, filename = nomenclature_utils.CGN_finder("3SN6",
                                                     try_web_lookup=False,
                                                     local_path=test_filenames.examples_path)

        assert isinstance(df, DataFrame)
        assert isinstance(filename,str)
        _np.testing.assert_array_equal(list(df.keys()),["CGN","Sort number","3SN6"])

    def test_works_online(self):
        df, filename = nomenclature_utils.CGN_finder("3SN6",
                                                     )

        assert isinstance(df, DataFrame)
        assert isinstance(filename, str)
        assert "http" in filename
        _np.testing.assert_array_equal(list(df.keys()), ["CGN", "Sort number", "3SN6"])

    def test_works_online_and_writes_to_disk_excel(self):
        with _TDir(suffix="_mdciao_test") as tdir:
            df, filename = nomenclature_utils.CGN_finder("3SN6",
                                                         format="%s.xlsx",
                                                         local_path=tdir,
                                                         write_to_disk=True
                                                         )

            assert isinstance(df, DataFrame)
            assert isinstance(filename, str)
            assert "http" in filename
            _np.testing.assert_array_equal(list(df.keys()), ["CGN", "Sort number", "3SN6"])
            assert path.exists(path.join(tdir,"3SN6.xlsx"))

    def test_works_online_and_writes_to_disk_ascii(self):
        with _TDir(suffix="_mdciao_test") as tdir:
            df, filename = nomenclature_utils.CGN_finder("3SN6",
                                                         local_path=tdir,
                                                         format="%s.txt",
                                                         write_to_disk=True
                                                         )

            assert isinstance(df, DataFrame)
            assert isinstance(filename, str)
            assert "http" in filename
            _np.testing.assert_array_equal(list(df.keys()), ["CGN", "Sort number", "3SN6"])
            assert path.exists(path.join(tdir,"3SN6.txt"))

    def test_works_local_does_not_overwrite(self):
        with _TDir(suffix="_mdciao_test") as tdir:
            infile = path.join(test_filenames.examples_path,"3SN6.txt")
            copy(infile,tdir)
            with pytest.raises(FileExistsError):
                nomenclature_utils.CGN_finder("3SN6",
                                              try_web_lookup=False,
                                              local_path=tdir,
                                              format="%s.txt",
                                              write_to_disk=True
                                              )



    def test_raises_not_find_locally(self):
        with pytest.raises(FileNotFoundError):
            nomenclature_utils.CGN_finder("3SN6",
                                          try_web_lookup=False
                                                     )

    def test_not_find_locally_but_no_fail(self):
        DF, filename = nomenclature_utils.CGN_finder("3SN6",
                                          try_web_lookup=False,
                                          dont_fail=True
                                                     )
        assert DF is None
        assert isinstance(filename,str)

    def test_raises_not_find_online(self):
        with pytest.raises(HTTPError):
            nomenclature_utils.CGN_finder("3SNw",
                                          )

    def test_not_find_online_but_no_raise(self):
        df, filename =    nomenclature_utils.CGN_finder("3SNw",
                                          dont_fail=True
                                          )
        assert df is None
        assert isinstance(filename,str)
        assert "www" in filename

class Test_GPCRmd_lookup_BW(unittest.TestCase):

    def test_works(self):
        DF = nomenclature_utils._BW_web_lookup("https://gpcrdb.org/services/residues/extended/adrb2_human")
        assert isinstance(DF, DataFrame)

    def test_wrong_code(self):
        with pytest.raises(ValueError):
            raise nomenclature_utils._BW_web_lookup("https://gpcrdb.org/services/residues/extended/adrb_beta2")

class Test_BW_finder(unittest.TestCase):

    def test_works_locally(self):
        df, filename = nomenclature_utils.BW_finder("B2AR",
                                                    try_web_lookup=False,
                                                    format="GPCRmd_%s_nomenclature_test.xlsx",
                                                    local_path=test_filenames.test_data_path)

        assert isinstance(df, DataFrame)
        assert isinstance(filename,str)
        _np.testing.assert_array_equal(list(df.keys()),["protein_segment","AAresSeq","BW","GPCRdb(A)","display_generic_number"])


    def test_works_online(self):
        df, filename = nomenclature_utils.BW_finder("adrb2_human",
                                                     )

        assert isinstance(df, DataFrame)
        assert isinstance(filename, str)
        assert "http" in filename
        _np.testing.assert_array_equal(list(df.keys()),["protein_segment","AAresSeq","BW","GPCRdb(A)","display_generic_number"])


    def test_raises_not_find_locally(self):
        with pytest.raises(FileNotFoundError):
            nomenclature_utils.BW_finder("B2AR",
                                          try_web_lookup=False
                                                     )

    def test_not_find_locally_but_no_fail(self):
        DF, filename = nomenclature_utils.BW_finder("B2AR",
                                          try_web_lookup=False,
                                          dont_fail=True
                                                     )
        assert DF is None
        assert isinstance(filename,str)


    def test_raises_not_find_online(self):
        with pytest.raises(ValueError):
            nomenclature_utils.BW_finder("B2AR",
                                          )

    def test_not_find_online_but_no_raise(self):
        df, filename =    nomenclature_utils.BW_finder("3SNw",
                                          dont_fail=True
                                          )
        assert df is None
        assert isinstance(filename,str)

class Test_table2BW_by_AAcode(unittest.TestCase):
    def setUp(self):
        self.file = test_filenames.GPCRmd_B2AR_nomenclature_test_xlsx

    def test_just_works(self):
        table2BW = table2BW_by_AAcode(tablefile = self.file)
        self.assertDictEqual(table2BW,
                             {'Q26': '1.25',
                              'E27': '1.26',
                              'E62': '12.48',
                              'R63': '12.49',
                              'T66': '2.37',
                              'V67': '2.38'
                              })

    def test_keep_AA_code_test(self): #dictionary keys will only have AA id
        table2BW = table2BW_by_AAcode(tablefile = self.file, keep_AA_code=False)
        self.assertDictEqual(table2BW,
                             {26: '1.25',
                              27: '1.26',
                              62: '12.48',
                              63: '12.49',
                              66: '2.37',
                              67: '2.38',
                           })

    def test_table2BW_by_AAcode_return_fragments(self):
        table2BW, defs = table2BW_by_AAcode(tablefile=self.file,
                                            return_fragments=True)

        self.assertDictEqual(defs,{'TM1':  ["Q26","E27"],
                                   "ICL1": ["E62","R63"],
                                   "TM2" : ["T66","V67"]})
    def test_table2B_by_AAcode_already_DF(self):
        from pandas import read_excel
        df = read_excel(self.file, header=0)

        table2BW = table2BW_by_AAcode(tablefile=df)
        self.assertDictEqual(table2BW,
                             {'Q26': '1.25',
                              'E27': '1.26',
                              'E62': '12.48',
                              'R63': '12.49',
                              'T66': '2.37',
                              'V67': '2.38'
                              })

class TestLabelerCGN(unittest.TestCase):

    # The setup is in itself a test
    def setUp(self):
        self._geom_3SN6 = md.load(path.join(test_filenames.examples_path,
                                            "3SN6.pdb.gz"))
        self.cgn_local = LabelerCGN("3SN6",
                                    try_web_lookup=False,
                               local_path=test_filenames.examples_path)

    def test_correct_files(self):


        _np.testing.assert_equal(self.cgn_local.tablefile,
                                 path.join(test_filenames.examples_path,"CGN_3SN6.txt"))
        _np.testing.assert_equal(self.cgn_local.ref_PDB,
                                 "3SN6")

    def test_mdtraj_attributes(self):
        pass
        #_np.testing.assert_equal(cgn_local.geom,
        #                         self._geom_3SN6)

        #_np.testing.assert_equal(cgn_local.top,
        #                         self._geom_3SN6.top)

    def test_dataframe(self):
        self.assertIsInstance(self.cgn_local.dataframe, DataFrame)
        self.assertSequenceEqual(list(self.cgn_local.dataframe.keys()),
                                 ["CGN","Sort number","3SN6"])

    def test_correct_residue_dicts(self):
        _np.testing.assert_equal(self.cgn_local.conlab2AA["G.hfs2.2"],"R201")
        _np.testing.assert_equal(self.cgn_local.AA2conlab["R201"],"G.hfs2.2")

    def test_correct_fragments_dict(self):
        # Test "fragments" dictionary SMH
        self.assertIsInstance(self.cgn_local.fragments,dict)
        assert all([len(ii)>0 for ii in self.cgn_local.fragments.values()])
        self.assertEqual(self.cgn_local.fragments["G.HN"][0],"T9")
        self.assertSequenceEqual(list(self.cgn_local.fragments.keys()),
                                 nomenclature_utils._CGN_fragments)

    def test_correct_fragments_as_conlabs_dict(self):
        # Test "fragments_as_conslabs" dictionary SMH
        self.assertIsInstance(self.cgn_local.fragments_as_conlabs, dict)
        assert all([len(ii) > 0 for ii in self.cgn_local.fragments_as_conlabs.values()])
        self.assertEqual(self.cgn_local.fragments_as_conlabs["G.HN"][0], "G.HN.26")
        self.assertSequenceEqual(list(self.cgn_local.fragments_as_conlabs.keys()),
                                 nomenclature_utils._CGN_fragments)

    def test_correct_fragment_names(self):
        self.assertSequenceEqual(self.cgn_local.fragment_names,
                                 list(self.cgn_local.fragments.keys()))

    def test_conlab2residx_wo_input_map(self):
        # More than anthing, this is testing _top2consensus_map
        # I know this a priori using find_AA
        out_dict = self.cgn_local.conlab2residx(self.cgn_local.top)
        self.assertEqual(out_dict["G.hfs2.2"], 164)

    def test_conlab2residx_w_input_map(self):
        # This should find R201 no problem

        map = [None for ii in range(200)]
        map[164] = "G.hfs2.2"
        out_dict = self.cgn_local.conlab2residx(self.cgn_local.top,map=map)
        self.assertEqual(out_dict["G.hfs2.2"],164)

    def test_conlab2residx_w_input_map_duplicates(self):
        map = [None for ii in range(200)]
        map[164] = "G.hfs2.2"  # I know this a priori using find_AA
        map[165] = "G.hfs2.2"
        with pytest.raises(ValueError):
            self.cgn_local.conlab2residx(self.cgn_local.top, map=map)

    def test_top2map_just_passes(self):
        # the true test of this is in the test of _top2consensus_map
        self.cgn_local.top2map(self.cgn_local.top)

    def test_top2defs_returns_all_keys(self):
        defs = self.cgn_local.top2defs(self.cgn_local.top, return_defs=True)
        self.assertSequenceEqual(list(defs.keys()),
                                 nomenclature_utils._CGN_fragments)

    def test_top2defs_defs_are_broken_in_frags(self):

        input_values = (val for val in ["0-1"])
        with mock.patch('builtins.input', lambda *x: next(input_values)):
            defs = self.cgn_local.top2defs(self.cgn_local.top,
                                           return_defs=True,
                                           fragments=[_np.arange(0,10),
                                                      _np.arange(10,15),
                                                      _np.arange(15,20)
                                                      ]
                                           )
            self.assertSequenceEqual(list(defs.keys()),
                                     nomenclature_utils._CGN_fragments)
            _np.testing.assert_array_equal(defs["G.HN"],_np.arange(0,15))

    def test_top2defs_defs_are_broken_in_frags_bad_input(self):
        input_values = (val for val in ["0-2"])
        with mock.patch('builtins.input', lambda *x: next(input_values)):  # Checking against the input 1 and 1
            with pytest.raises(ValueError):
                self.cgn_local.top2defs(self.cgn_local.top,
                                        return_defs=True,
                                           fragments=[_np.arange(0, 10),
                                                      _np.arange(10, 15),
                                                      _np.arange(15, 40)]
                                           )


class TestLabelerBWwoPDB(unittest.TestCase):

    # The setup is in itself a test
    def setUp(self):
        self.BW_local_no_pdb = LabelerBW("B2AR",
                                         format="GPCRmd_%s_nomenclature_test.xlsx",
                                         local_path=test_filenames.test_data_path)

    def test_correct_files(self):
        _np.testing.assert_equal(self.BW_local_no_pdb.tablefile,
                                 path.join(test_filenames.test_data_path,
                                           "GPCRmd_B2AR_nomenclature_test.xlsx"))
        _np.testing.assert_equal(self.BW_local_no_pdb.ref_PDB,
                                 None)

class TestLabelerBWwPDB(unittest.TestCase):

    # The setup is in itself a test
    def setUp(self):
        self.BW_local_w_pdb = LabelerBW("B2AR",
                                        ref_PDB="3SN6",
                                        format="GPCRmd_%s_nomenclature_test.xlsx",
                                        local_path=test_filenames.test_data_path)

    def test_correct_files(self):
        _np.testing.assert_equal(self.BW_local_w_pdb.tablefile,
                                 path.join(test_filenames.test_data_path,
                                           "GPCRmd_B2AR_nomenclature_test.xlsx"))
        _np.testing.assert_equal(self.BW_local_w_pdb.ref_PDB,
                                 "3SN6")

    def test_mdtraj_attributes(self):
        pass
        # _np.testing.assert_equal(cgn_local.geom,
        #                         self._geom_3SN6)

        # _np.testing.assert_equal(cgn_local.top,
        #                         self._geom_3SN6.top)

    def test_dataframe(self):
        self.assertIsInstance(self.BW_local_w_pdb.dataframe, DataFrame)
        self.assertSequenceEqual(list(self.BW_local_w_pdb.dataframe.keys()),
                                 ['protein_segment', 'AAresSeq', 'BW', 'GPCRdb(A)', 'display_generic_number'])

    def test_correct_residue_dicts(self):
        _np.testing.assert_equal(self.BW_local_w_pdb.conlab2AA["1.25"],"Q26")
        _np.testing.assert_equal(self.BW_local_w_pdb.AA2conlab["Q26"],"1.25")

    def test_correct_fragments_dict(self):
        # Test "fragments" dictionary SMH
        self.assertIsInstance(self.BW_local_w_pdb.fragments,dict)
        assert all([len(ii)>0 for ii in self.BW_local_w_pdb.fragments.values()])
        self.assertEqual(self.BW_local_w_pdb.fragments["ICL1"][0],"E62")
        self.assertSequenceEqual(list(self.BW_local_w_pdb.fragments.keys()),
                                 ["TM1","ICL1","TM2"])

    def test_correct_fragments_as_conlabs_dict(self):
        # Test "fragments_as_conslabs" dictionary SMH
        self.assertIsInstance(self.BW_local_w_pdb.fragments_as_conlabs, dict)
        assert all([len(ii) > 0 for ii in self.BW_local_w_pdb.fragments_as_conlabs.values()])
        self.assertSequenceEqual(list(self.BW_local_w_pdb.fragments_as_conlabs.keys()),
                                 ["TM1", "ICL1", "TM2"])
        self.assertEqual(self.BW_local_w_pdb.fragments_as_conlabs["TM1"][0], "1.25")

    def test_correct_fragment_names(self):
        self.assertSequenceEqual(self.BW_local_w_pdb.fragment_names,
                                 list(self.BW_local_w_pdb.fragments.keys()))

class Test_intersecting_fragments(unittest.TestCase):

    def setUp(self):
        self.fragments = [_np.arange(0,5),
                          _np.arange(5,10),
                          _np.arange(10,15)
                          ]
        self.top = md.load(test_filenames.prot1_pdb).top
        self.map_conlab = ["%u_%s"%(rr.index,str(rr)) for rr in self.top.residues]

    def test_no_clashes(self):
        result = nomenclature_utils._intersecting_fragments([6,7,8],
                                                            "test_frag",
                                                            self.fragments,
                                                            self.top,
                                                            )
        _np.testing.assert_array_equal(result, [6,7,8])

    def test_clashes(self):
        input_values = (val for val in ["0"])
        with mock.patch('builtins.input', lambda *x: next(input_values)):  # Checking against the input 1 and 1
            result = nomenclature_utils._intersecting_fragments(_np.arange(3,9),
                                                            "test_frag",
                                                            self.fragments,
                                                            self.top,
                                                            )
            _np.testing.assert_array_equal(result,[3,4])

    def test_clashes_keeps_all(self):
        result = nomenclature_utils._intersecting_fragments(_np.arange(3, 9),
                                                            "test_frag",
                                                            self.fragments,
                                                            self.top,
                                                            keep_all=True)
        _np.testing.assert_array_equal(_np.arange(3,9),result)

class Test_choose_between_consensus_dicts(unittest.TestCase):

    def test_works(self):
        str = nomenclature_utils._choose_between_consensus_dicts(1,
                                                                 [{1:"BW1"},
                                                                  {1:None}])
        assert str=="BW1"

    def test_not_found(self):
        str = nomenclature_utils._choose_between_consensus_dicts(1,
                                                                 [{1: None},
                                                                  {1: None}],
                                                                 no_key="NAtest")
        assert str == "NAtest"

    def test_raises(self):
        with pytest.raises(AssertionError):
            nomenclature_utils._choose_between_consensus_dicts(1,
                                                               [{1: "BW1"},
                                                                {1: "CGN1"}],
                                                              )


@unittest.skip("The tested method appears to be unused")
class Test_guess_missing_BWs(unittest.TestCase):
    #TODO change this test to reflect the new changes Guillermo recently added
    def setUp(self):
        self.file = path.join(test_filenames.GPCRmd_B2AR_nomenclature_test_xlsx)
        self.geom = md.load(test_filenames.file_for_test_pdb)

    def _test_guess_missing_BWs_just_works(self):
        table2BW = table2BW_by_AAcode(tablefile=self.file)
        guess_BW = guess_missing_BWs(table2BW, self.geom.top, restrict_to_residxs=None)
        self.assertDictEqual(guess_BW,
                             {0: '1.29*',
                              1: '1.30*',
                              2: '1.31*',
                              3: '1.27*',
                              4: '1.26',
                              5: '1.27*',
                              6: '1.28*',
                              7: '1.28*'})

@unittest.skip("The tested method appears to be unused")
class Test_top2CGN_by_AAcode(unittest.TestCase):
    #TODO change this test to reflect the new changes Guillermo recently added
    def setUp(self):
        self.cgn = LabelerCGN("3SN6",
                              local_path=test_filenames.examples_path)
        self.geom = md.load(test_filenames.file_for_test_pdb)

    def _test_top2CGN_by_AAcode_just_works(self):
        top2CGN = top2CGN_by_AAcode(self.geom.top, self.cgn)
        self.assertDictEqual(top2CGN,
                             {0: 'G.HN.27',
                              1: 'G.HN.53',
                              2: 'H.HC.11',
                              3: 'H.hdhe.4',
                              4: 'G.S2.3',
                              5: 'G.S2.5',
                              6: None,
                              7: 'G.S2.6'})

@unittest.skip("This method appears unused at the moment")
class Test_add_loop_definitions_to_TM_residx_dict(unittest.TestCase):
    def setUp(self):
        self.segment_dict = {'TM1': [20, 21, 22], 'TM2': [30, 33, 34], 'TM3': [40, 48], 'TM4': [50, 56],
                             'TM5': [60, 61],'TM6': [70], 'TM7': [80, 81, 82, 83, 89], 'H8': [90, 91, 92, 93, 94, 95]}

    def test_add_loop_definitions_to_TM_residx_dict_just_works(self):
        add_defs = add_loop_definitions_to_TM_residx_dict(self.segment_dict)
        self.assertEqual(add_defs['ICL1'],[23, 29])
        self.assertEqual(add_defs['ECL1'], [35, 39])
        self.assertEqual(add_defs['ICL2'], [49, 49])
        self.assertEqual(add_defs['ECL2'], [57, 59])
        self.assertEqual(add_defs['ECL3'], [71, 79])

class Test_map2defs(unittest.TestCase):
    def setUp(self):
        self.cons_list =  ['3.67','G.H5.1','G.H5.6','5.69']

    def test_map2defs_just_works(self):
        map2defs = nomenclature_utils._map2defs(self.cons_list)
        assert (_np.array_equal(map2defs['3'], [0]))
        assert (_np.array_equal(map2defs['G.H5'], [1, 2]))
        assert (_np.array_equal(map2defs['5'], [3]))

class Test_top2consensus_map(unittest.TestCase):
    #TODO add test for special case restrict_to_residxs
    def setUp(self):
        self.cgn = LabelerCGN("3SN6",
                              local_path=test_filenames.examples_path,
                              )
        self.geom = md.load(test_filenames.file_for_top2consensus_map)
        self.cons_list_test = ['G.HN.26','G.HN.27','G.HN.28','G.HN.29','G.HN.30']
        self.cons_list_keep_consensus = ['G.hfs2.1', 'G.hfs2.2', 'G.hfs2.3', 'G.hfs2.4',
                                         'G.hfs2.5', 'G.hfs2.6', 'G.hfs2.7']

    def test_top2consensus_map_just_works(self): #generally works
        cons_list = nomenclature_utils._top2consensus_map(consensus_dict=self.cgn.AA2conlab, top=self.geom.top)

        count = 1
        cons_list_out = []
        for ii, val in enumerate(cons_list):
            if val is not None:
                cons_list_out.append(val)
                count += 1
            if count > 5: #testing for the first 5 entries in the pdb file which have a valid CGN name
                break
        self.assertEqual(cons_list_out, self.cons_list_test)

    def test_top2consensus_map_keep_consensus_is_true(self):
        #In the output below, instead of None, None, it will be 'G.hfs2.4' and 'G.hfs2.5'
        # ['G.hfs2.1', 'G.hfs2.2', 'G.hfs2.3', None, None, 'G.hfs2.6', 'G.hfs2.7']
        cons_list = nomenclature_utils._top2consensus_map(consensus_dict=self.cgn.AA2conlab, top=self.geom.top, keep_consensus=True)
        cons_list_out = []

        for ii, val in enumerate(cons_list):
            if (ii > 434 and ii < 442):
                cons_list_out.append(val)
        self.assertEqual(cons_list_out, self.cons_list_keep_consensus)

class Test_fill_CGN_gaps(unittest.TestCase):
    def setUp(self):
        self.geom = md.load(test_filenames.file_for_top2consensus_map)
        self.cons_list_in = ['G.hfs2.1', 'G.hfs2.2', 'G.hfs2.3', None,
                          None, 'G.hfs2.6', 'G.hfs2.7']
        self.cons_list_out = ['G.hfs2.1', 'G.hfs2.2', 'G.hfs2.3', 'G.hfs2.4',
                                         'G.hfs2.5', 'G.hfs2.6', 'G.hfs2.7']


    def test_fill_CGN_gaps_just_works_with_CGN(self):
        fill_cgn = nomenclature_utils._fill_consensus_gaps(self.cons_list_in, self.geom.top)
        self.assertEqual(fill_cgn,self.cons_list_out)


class Test_fill_BW_gaps(unittest.TestCase):
    def setUp(self):
        self.geom = md.load(test_filenames.prot1_pdb)
        self.cons_list_in = ['3.46', '3.47', "3.48", None,
                             None, '3.51', '3.52']
        self.cons_list_out = ['3.46', '3.47', "3.48", "3.49",
                             "3.50", '3.51', '3.52']

    def test_fill_CGN_gaps_just_works_with_BW(self):
        fill_cgn = nomenclature_utils._fill_consensus_gaps(self.cons_list_in, self.geom.top)
        self.assertEqual(fill_cgn, self.cons_list_out)

@unittest.skip("This method apperas unused at the moment")
class Test_fill_BW_gaps_old(unittest.TestCase):
    def setUp(self):
        self.geom = md.load(test_filenames.file_for_top2consensus_map)
        self.cons_list_in = ['1.25', '1.26', None, '1.28']
        self.cons_list_out = ['1.25', '1.26', '1.27', '1.28']

    def test_fill_BW_gaps_just_works(self):
        fill_bw = nomenclature_utils._fill_BW_gaps(self.cons_list_in, self.geom.top)
        self.assertEqual(fill_bw,self.cons_list_out)


class Test_guess_by_nomenclature(unittest.TestCase):

    def setUp(self):
        self.BW_local_w_pdb = LabelerBW("adrb2_human",
                                        ref_PDB="3SN6",
                                        format="%s_full.xlsx",
                                        local_path=test_filenames.test_data_path)
        self.fragments = get_fragments(self.BW_local_w_pdb.top)

    def test_works_on_enter(self):
        import mock
        input_values = (val for val in [""])
        with mock.patch('builtins.input', lambda *x: next(input_values)):
            answer = nomenclature_utils._guess_by_nomenclature(self.BW_local_w_pdb,
                                                              self.BW_local_w_pdb.top,
                                                              self.fragments,
                                                              "BW")
            self.assertEqual(answer,"7,8,9")

    def test_works_return_answer_as_list(self):
        import mock
        input_values = (val for val in [""])
        with mock.patch('builtins.input', lambda *x: next(input_values)):
            answer = nomenclature_utils._guess_by_nomenclature(self.BW_local_w_pdb,
                                                              self.BW_local_w_pdb.top,
                                                              self.fragments,
                                                              "BW",
                                                               return_str=False,
                                                                       )
            self.assertSequenceEqual(answer,[7,8,9])

    def test_works_return_guess(self):
        answer = nomenclature_utils._guess_by_nomenclature(self.BW_local_w_pdb,
                                                          self.BW_local_w_pdb.top,
                                                          self.fragments,
                                                          "BW",
                                                           accept_guess=True
                                                           )
        self.assertEqual(answer, "7,8,9")

    def test_works_return_None(self):
        answer = nomenclature_utils._guess_by_nomenclature(self.BW_local_w_pdb,
                                                           self.BW_local_w_pdb.top,
                                                           self.fragments,
                                                           "BW",
                                                           accept_guess=True,
                                                           min_hit_rate=2, #impossible rate
                                                           )
        self.assertEqual(answer, None)

class Test_guess_nomenclature_fragments(unittest.TestCase):
    # The setup is in itself a test
    def setUp(self):
        self.BW_local_w_pdb = LabelerBW("adrb2_human",
                                        ref_PDB="3SN6",
                                        format="%s_full.xlsx",
                                        local_path=test_filenames.test_data_path)
        self.fragments = get_fragments(self.BW_local_w_pdb.top)

    def test_finds_frags(self):
        guessed_frags = nomenclature_utils._guess_nomenclature_fragments(self.BW_local_w_pdb,
                                                         self.BW_local_w_pdb.top,
                                                         fragments=self.fragments,
                                                         verbose=True)
        _np.testing.assert_array_equal([7,8,9],guessed_frags)

if __name__ == '__main__':
    unittest.main()

