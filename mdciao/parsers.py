import argparse

# https://stackoverflow.com/questions/3853722/python-argparse-how-to-insert-newline-in-the-help-text
class SmartFormatter(argparse.HelpFormatter):

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)

def _inform_of_parser(parser,args=None):
    r"""
    Print all the valuesof the variables in a parser
    TODO find out the native way of doing this
    Parameters
    ----------
    parser

    Returns
    -------

    """
    # TODO is this too hacky, wouldn't *args suffice?
    # This is just to run tests
    if args is None:
        a = parser.parse_args()
    else:
        a = parser.parse_args(args)
    for key, __ in a._get_kwargs():
        dval = parser.get_default(key)
        fmt = '%s=%s,'
        if isinstance(dval, str):
            fmt = '%s="%s",'
        print(fmt % (key, dval))

def _parser_top_traj(description=None):
    r"""
    Instantiate the basic parsers which can take topology and trajectories

    Parameters
    ----------
    description: str
        The initial description of the parser

    Returns
    -------

    """
    parser = argparse.ArgumentParser(description=description, formatter_class=SmartFormatter)
    _parser_add_topology(parser)
    _parser_add_trajectories(parser)
    return parser

def _parser_add_trajectories(parser):
    parser.add_argument('trajectories', type=str, help='trajectory file(s)', nargs='+')

def _parser_add_topology(parser):
    parser.add_argument('topology', type=str, help='Topology file')

def _parser_add_cutoff(parser):
    parser.add_argument("--ctc_cutoff_Ang", type=float,
                        help="The cutoff distance between two residues for them to be considered in contact. "
                             "Default is 3.5 Angstrom.",
                        default=3.5)

def _parser_add_n_neighbors(parser, default=4):
    parser.add_argument("--n_nearest", type=int,
                        help="Ignore this many nearest neighbors when computing neighbor lists."
                             " 'Near' means 'connected by this many bonds'. Default is %u."%default,
                        default=default)

def _parser_add_stride(parser,
                       help="Stride down the input trajectoy files by this factor. Default is 1." ):
    parser.add_argument("--stride", type=int,
                        help=help, default=1)

def _parser_add_chunk(parser,help="Trajectories are read in chunks of this size. "
                                  "Helps with big files and/or large number of contacts"
                                  " when you run into memory problems. Default is %s",
                      default=10000):
    parser.add_argument("--chunksize_in_frames", type=int,
                        help=help%default,
                        default=default)

def _parser_add_time_traces(parser):
    parser.add_argument('--time-trace', dest="plot_timedep", action='store_true',
                        help='Plot time-traces of the contacts, default is True')
    parser.add_argument('--no-time-trace', dest="plot_timedep", action='store_false',
                       )
    parser.set_defaults(plot_timedep=True)

def _parser_add_distro(parser):
    parser.add_argument('-d', '--distribution', dest="distro", action='store_true',
                        help='Plot distance distributions instead of contact bar plots. Default is False.')

    parser.set_defaults(distro=False)

def _parser_add_smooth(parser):
    parser.add_argument("--n_smooth_hw", type=int,
                        help="Number of frames one half of the averaging window for the time-traces. Default is 0, which means no averaging.",
                        default=0)

def _parser_add_scheme(parser):
    parser.add_argument("--scheme",type=str, default='closest-heavy',
                        help="Type for scheme for computing distance between residues. Choices are "
                             "{'ca', 'closest', 'closest-heavy', 'sidechain', 'sidechain-heavy'}. "
                             "See mdtraj documentation for more info")

def _parser_add_ylim_Ang(parser):
    parser.add_argument("--ylim_Ang",type=str, default="10",
                        help="Limit in Angstrom of the y-axis of the time-traces. Default is 10. "
                             "Switch to any other float or 'auto' for automatic scaling")

def _parser_add_t_unit(parser):
    parser.add_argument("--t_unit", type=str,
                        help="Unit used for the temporal axis, default is ns.",
                        default="ns")

def _parser_add_curve_color(parser):
    parser.add_argument("--curve_color", type=str,
                        help="Type of color used for the curves. Default is auto. Alternatives are 'Peter' or 'Hobat'",
                        default="auto")

def _parser_add_gray_backgroud(parser):
    parser.add_argument('--gray-background', dest='gray_background', action='store_true',
                        help="Use gray background when using smoothing windows"
                             " Defaut is False")
    parser.add_argument('--no-gray-background', dest='gray_background', action='store_false')
    parser.set_defaults(gray_background=False)

def _parser_add_fragments(parser):
    parser.add_argument("-fr",'--fragments', default=['lig_resSeq+'], nargs='+',
                        help=("R|How to sub-divide the topology into fragments.\n"
                              "Several options possible. Taking the example sequence:\n"
                              "…-A27,Lig28,K29-…-W40,D45-…-W50,CYSP51,GDP52\n"
                              " - 'resSeq'\n"
                              "     breaks at jumps in resSeq entry:\n"
                              "     […A27,Lig28,K29,…,W40],[D45,…,W50,CYSP51,GDP52]\n"
                              " - 'resSeq+'\n"
                              "     breaks only at negative jumps in resSeq:\n"
                              "     […A27,Lig28,K29,…,W40,D45,…,W50,CYSP51,GDP52]\n"
                              " - 'bonds'\n"
                              "     breaks when AAs are not connected by bonds,\n"
                              "     ignores resSeq:\n"
                              "     […A27][Lig28],[K29,…,W40],[D45,…,W50],[CYSP51],[GDP52]\n"""
                              "     notice that because phosphorylated CYSP51 didn't get a\n"
                              "     bond in the topology, it's considered a ligand\n"
                              " - 'resSeq_bonds'\n"
                              "     breaks both at resSeq jumps or missing bond\n"
                              " -  'lig_resSeq+\n'"
                              "     Like resSeq+ but put's any non-AA residue into\n"
                              "     it's own fragment:\n"
                              "     […A27][Lig28],[K29,…,W40],[D45,…,W50,CYSP51],[GDP52]\n"
                              " -  'chains'\n"
                              "     breaks into chains of the PDB file/entry\n"
                              " -   None or 'None\n'"
                              "     all residues are in one fragment, fragment 0\n"                              
                              " - 'consensus'\n"
                              "     If any consensus nomenclature is provided,\n"
                              "     ask the user for definitions using\n"
                              "     consensus labels\n"
                              " - 0-10,15,14 20,21,30-50 51 (example, advanced users only)\n" 
                              "     Input arbitrary fragments via their\n"
                              "     residue serial indices (zero-indexed) using space as\n"
                              "     separator. Not recommended\n."
                              " - 'None'\n"
                              "     All residues are in one fragment (fragment 0)\n"
                              "     Can be harmless or potentially dangerous if residue\n "
                              "     labels are repeated."
                              "If you are unsure of any of these options, use \n"
                              "the command line tool mdc_fragments.py on \n"
                              "your topology file."))

def _parser_add_output_dir(parser):
    parser.add_argument('-od','--output_dir', type=str, help="directory to which the results are written. Default is '.'",
                        default='.')

def _parser_add_nomenclature(parser):
    parser.add_argument("--BW_uniprot", type=str,
                        help="Look for Ballesteros-Weinstein definitions in the GPRCmd using a uniprot code, "
                             "e.g. adrb2_human. See https://gpcrdb.org/services/ for more details."
                             "Default is None.",
                        default='None')
    parser.add_argument("--BW_write",dest='write_to_disk_BW',action="store_true",
                        help='Write the BW definitions to disk so that it can be acessed locally in later uses. '
                             'Default is False',
                        default=False)
    parser.add_argument("--no-BW_write", dest='write_to_disk_BW', action="store_false",
                        default=True)
    parser.set_defaults(write_to_disk_BW=False)
    parser.add_argument("--CGN_PDB", type=str, help="PDB code for a consensus G-protein nomenclature", default='None')

def _parser_add_graphic_ext(parser):
    parser.add_argument('-gx','--graphic_ext', type=str, help="Extension of the output graphics, default is .pdf",
                        default='.pdf')

def _parser_add_no_fragfrag(parser):
    parser.add_argument('--same_fragment', dest='same_fragment', action='store_true',
                        help="Allow contact partners in the same fragment, default is True"
                             " Defaut is True")
    parser.add_argument('--no-same_fragment', dest='same_fragment', action='store_false')
    parser.set_defaults(allow_same_fragment_ctcs=True)

def _parser_add_pbc(parser):
    parser.add_argument('--no-pbc', dest='pbc',
                        help="Do not consider periodic boundary conditions when computing distances."
                             " Defaut is to consider them",
                        action='store_false')
    parser.set_defaults(pbc=True)

def _parser_add_short_AA_names(parser):
    parser.add_argument('-sa','--short_AAs', dest='short_AA_names', action='store_true',
                        help="Use one-letter aminoacid names when possible, e.g. K145 insted of Lys145."
                             " Defaut is False")
    parser.set_defaults(short_AA_names=False)

def _parser_add_output_desc(parser, default='output_sites'):
    parser.add_argument('-o','--output_desc', type=str, help="Descriptor for output files. Default is %s"%default,
                        default=default)
    return parser


def _parser_add_title(parser):
    parser.add_argument("-t", "--title", default=None, type=str,
                        help="Name of the system. Used for figure titles (not filenames)"
                             "Defaults to --output_desc if None is given")

def _parser_add_n_jobs(parser):
    parser.add_argument("--n_jobs", type=int, default=1, help="Number of processors to use. "
                                                              "The parallelization is done over trajectories and "
                                                              "not over contacts, beyond n_jobs>n_trajs "
                                                              "parallelization will not have any effect.")

def _parser_add_sites(parser):
    parser.add_argument('--site_files', type=str, nargs='+',
                        help='site file(s) in json format containing site information, i.e., which bonds correspond to each site')

def _parser_add_fragment_names(parser):
    parser.add_argument('--fragment_names', type=str,
                        help="Name of the fragments. Leave empty if you want them automatically named."
                             " Otherwise, give a quoted list of strings separated by commas, e.g. "
                             "'TM1, TM2, TM3,'",
                        default="")

def _parser_add_n_ctcs(parser, default=5):
    parser.add_argument("-nc", "--n_ctcs", type=int,
                        help="Only the first n_ctcs most-frequent contacts "
                             "will be written to the ouput. Default is %u."%default,
                        default=default)

def _parser_add_pop(parser):
    parser.add_argument("--pop_N_ctcs", dest="separate_N_ctcs", action="store_true",
                        help="Separate the plot with the total number contacts from the time-trace plot. "
                             "Default is False")
    parser.add_argument("--no-pop_N_ctcs", dest="separate_N_ctcs", action="store_false")
    parser.set_defaults(separate_N_ctcs=False)

def _parser_add_n_cols(parser):
    parser.add_argument("--n_cols", type=int, help="number of columns of the overall plot. Default is 4",
                        default=4)

def _parser_add_graphic_dpi(parser):
    parser.add_argument('--graphic_dpi', type=int,
                        help="Dots per Inch (DPI) of the graphic output. Only has an effect for bitmap outputs. Default is 150.",
                        default=150)

def _parser_add_table_ext(parser):
    parser.add_argument('-tx','--table_ext', type=str,
                        help="Extension for tabled files (.dat, .txt, .xlsx). Default is 'none', which does not write anything.",
                        default=None)

def _parser_add_write_to_disk(parser):
    parser.set_defaults(write_to_disk=False)
    parser.add_argument("--keep",
                        help="Save the consensus file locally for later use, default is False",
                        dest="write_to_disk", action="store_true"
                        )
def _parser_add_print_conlab(parser):
    parser.set_defaults(print_conlab=False)
    parser.add_argument("--verbose",
                        help="Print the consensus labels for all residues",
                        dest="print_conlab", action="store_true"
                        )
def _parser_add_fill_gaps(parser):
    parser.set_defaults(fill_gaps=False)
    parser.add_argument("--autofill",
                        help="Try to guess missing consensus labels",
                        dest="fill_gaps", action="store_true"
                        )
def _parser_add_AAs(parser):
    parser.add_argument("--AAs",type=str,
                        help="Print the idxs and labels of these AAs, e.g. R131,GLU30",
                        default=None)

def _parser_add_atomtypes(parser):
    parser.add_argument("-at", "--atomtypes",
                        dest="plot_atomtypes", action="store_true",
                        help="Add the atom-types to the frequency bars by 'hatching' them.\n"
                             " '--' is sidechain-sidechain\n"
                             " '|' is backbone-backbone\n"
                             " '\\' is backbone-sidechain\n"
                             " '/' is sidechain-backbone\n"
                             "Default is false")
    parser.set_defaults(accept_guess=False)

def _parser_add_conslabels(parser):
    parser.add_argument("--labels",type=str,
                        help="Print the idxs and resnames of these consensus labels, e.g. 3.50,2.63",
                        default=None)
def _parser_add_residues(parser):
    parser.add_argument('-r', '--residues', type=str,
                        help='The residues of interest, as coma-separated-values without spaces.\n'
                             'The input is very flexible and accepts\n'
                             'mixed descriptors and wildcards, eg: "GLU*,ARG*,GDP*,LEU394,380-385"\n'
                             "is a valid input. Numbers are interpeted as a residue's sequence number\n"
                             " (394 in LEU394), unless --serial_idxs is passed as an option.")

def _parser_add_no_frag(parser):
    parser.add_argument('-nf',"--no-fragments", dest='fragmentify',action='store_false',
                        help="Do not use fragments. Defautl is to use them")
    parser.set_defaults(fragmentify=True)

#TODO unify _ vs - in arguments
def _parser_add_frag_colors(parser):
    parser.add_argument("--fragment_colors", type=str,
                        help="comma-separated vales of the fragment colors.\n"
                             " If only one value, use that color for all fragments\n"
                             " Any matplotlib colors can be used. Default is 'tab:blue'\n"
                             " Why 'tab'? check https://matplotlib.org/3.1.1/tutorials/colors/colors.html !",
                        default="tab:blue")

def _paser_add_guess(parser):
    parser.add_argument("-ni", "-no-interactive",
                        dest="accept_guess", action="store_true",
                        help="Try not to be interactive. This can make wrong choices for the user, advanded only.")
    parser.set_defaults(accept_guess=False)

# TODO group the parser better!
# TODO add short versions of the most frequent options
def parser_for_rn():
    parser = _parser_top_traj(description='Analyse residue neighborhoods using a distance cutoff. '
                                          'residue-residue contacts are reported in terms of their'
                                          'overall frequencies and time-traces. A number of files '
                                          'containing plots, tables and data will be generated.' )

    _parser_add_residues(parser)
    _parser_add_cutoff(parser)

    parser.add_argument('--serial_idxs', dest='res_idxs', action='store_true',
                        help='Interpret the indices of --residues '
                             'not as their sequence idxs (e.g. 30 for GLU30), but as '
                             'their serial order in the topology (e.g. 0 for GLU30 if '
                             'GLU30 is the first residue in the topology). Default is False')
    parser.set_defaults(res_idxs=False)

    _parser_add_stride(parser)
    _parser_add_n_ctcs(parser)
    _parser_add_n_neighbors(parser)
    _parser_add_chunk(parser)
    _parser_add_smooth(parser)
    parser.add_argument("--nlist_cutoff_Ang", type=float,
                        help="Cutoff for the initial neighborlist. Only atoms that are \n"
                             "within this distance in the original reference \n"
                             "(the topology file) are considered potential neighbors \n"
                             "of the --residues, s.t. non-necessary distances \n"
                             " (e.g. between the receptor's N-terminus and G-protein) are not even computed. "
                             "Default is 15 Angstrom.", default=15)
    _parser_add_fragments(parser)
    _parser_add_fragment_names(parser)
    _parser_add_no_frag(parser)
    _parser_add_frag_colors(parser)
    parser.add_argument('--no-sort', dest='sort',
                        help="Don't sort the residues by their index. Defaut is to sort them.",
                        action='store_false')
    parser.set_defaults(sort=True)

    _parser_add_pbc(parser)

    parser.add_argument('--ask_fragment', dest='ask', action='store_true',
                        help="Interactively ask for fragment assignment when input matches more than one resSeq")
    parser.add_argument('--no-ask_fragment', dest='ask', action='store_false')
    parser.set_defaults(ask=True)
    _parser_add_table_ext(parser)
    _parser_add_graphic_ext(parser)



    _parser_add_nomenclature(parser)
    _parser_add_output_dir(parser)
    _parser_add_output_desc(parser, default='neighborhood')
    _parser_add_t_unit(parser)
    _parser_add_curve_color(parser)
    _parser_add_gray_backgroud(parser)
    _parser_add_graphic_dpi(parser)
    _parser_add_short_AA_names(parser)
    #_parser_add_no_fragfrag(parser)
    _parser_add_time_traces(parser)
    _parser_add_distro(parser)
    _parser_add_n_cols(parser)
    _parser_add_n_jobs(parser)
    _parser_add_pop(parser)
    _parser_add_ylim_Ang(parser)
    _paser_add_guess(parser)
    _parser_add_switch(parser)
    return parser

def _parser_add_switch(parser):
    parser.add_argument("-s","--switch_off_Ang",
                        default=None,
                        type=float,
                        help="Use a linear switchoff instead of a crisp one. Deafault is None")
def parser_for_dih():
    parser = _parser_top_traj(description='Small analysis tool for computation of residue dihedrals, backbone and sidechains.')


    parser.add_argument('--resSeq_idxs', type=str,
                        help='the resSeq idxs of interest (in VMD these are called "resid"). '
                             'Can be in a format 1,2-6,10,20-25. No spaces are allowed.')
    parser.add_argument('--types',type=str,default='all', help='Types of dihedral angles to be computed. It can be '
                                                               'an "all", "backbone", or "sidechain"')
    _parser_add_stride(parser)
    _parser_add_chunk(parser)
    _parser_add_smooth(parser)
    #_parser_add_fragments(parser)
    _parser_add_fragment_names(parser)

    parser.add_argument('--sort', dest='sort', action='store_true', help="Sort the resSeq_idxs list. Defaut is True")
    parser.add_argument('--no-sort', dest='sort', action='store_false')
    parser.set_defaults(sort=True)

    #parser.add_argument('--pbc', dest='pbc', action='store_true',
    #                    help="Consider periodic boundary conditions when computing distances."
    #                         " Defaut is True")
    #parser.add_argument('--no-pbc', dest='pbc', action='store_false')
    #parser.set_defaults(pbc=True)

    parser.add_argument('--ask_fragment', dest='ask', action='store_true',
                        help="Interactively ask for fragment assignemnt when input matches more than one resSeq")
    parser.add_argument('--no-ask_fragment', dest='ask', action='store_false')
    parser.set_defaults(ask=True)
    parser.add_argument('--output_npy', type=str, help="Name of the output.npy file for storing this runs' results",
                        default='output.npy')
    _parser_add_table_ext(parser)
    parser.add_argument('--graphic_ext', type=str, help="Extension of the output graphics, default is .pdf",
                        default='.pdf')

    parser.add_argument('--serial_idxs', dest='res_idxs', action='store_true',
                        help='Interpret the indices of --resSeq_idxs '
                             'not as sequence idxs (e.g. 30 for GLU30), but as '
                             'their order in the topology (e.g. 0 for GLU30 if '
                             'GLU30 is the first residue in the topology). Default is False')
    parser.set_defaults(res_idxs=False)

    _parser_add_nomenclature(parser)
    _parser_add_output_dir(parser)
    _parser_add_output_desc(parser, default='dih')
    _parser_add_t_unit(parser)
    _parser_add_curve_color(parser)
    _parser_add_gray_backgroud(parser)
    _parser_add_graphic_dpi(parser)
    _parser_add_short_AA_names(parser)
    _parser_add_time_traces(parser)
    _parser_add_n_cols(parser)
    _parser_add_n_jobs(parser)

    parser.add_argument('--degrees',   dest='use_deg', action="store_true", help='Use degrees (default) or radians')
    parser.add_argument('--no-degrees',dest='use_deg', action="store_false")
    parser.set_defaults(use_deg=True)

    parser.add_argument('--cos',   dest='use_cos', action="store_true", help="Use the cosine of the angle instead of the angle. Default is not to use cosine")
    parser.add_argument('--no-cos',dest='use_cos', action="store_false")
    parser.set_defaults(use_cos=True)

    return parser

def parser_for_sites():
    #todo THIS WILL BREAK PARSER FOR SITES!!!! HUH?
    parser = _parser_top_traj(description='Analyse a specific set of residue-residue contacts using a distance cutoff. '
                                          'The user has to provide one or more "site" files in a .json format')

    _parser_add_sites(parser)
    parser.add_argument('--default_fragment_index', default=None, type=int,
                        help="In case a residue identified as, e.g, GLU30, appears more than\n"
                             " one time in the topology, e.g. in case of a dimer, the user can\n"
                             " pass which fragment/monomer should be chosen by default. The\n"
                             " default behaviour (None) will prompt the user when necessary")
    _parser_add_scheme(parser)
    _parser_add_nomenclature(parser)
    _parser_add_output_dir(parser)
    _parser_add_output_desc(parser,default="sites")
    _parser_add_stride(parser)
    _parser_add_smooth(parser)
    _parser_add_no_frag(parser)
    #_parser_add_fragment_names(parser)
    _parser_add_cutoff(parser)
    _parser_add_t_unit(parser)
    _parser_add_graphic_ext(parser)
    _parser_add_curve_color(parser)
    _parser_add_gray_backgroud(parser)
    _parser_add_graphic_dpi(parser)
    _parser_add_ylim_Ang(parser)
    _parser_add_short_AA_names(parser)
    _parser_add_n_jobs(parser)
    _parser_add_table_ext(parser)
    _parser_add_atomtypes(parser)
    _paser_add_guess(parser)
    return parser

def parser_for_densities():
    parser = _parser_top_traj("For densities")
    _parser_add_sites(parser)
    _parser_add_output_dir(parser)
    _parser_add_stride(parser,help='Stride down the data by this factor. Default is 1.')

    return parser

def parser_for_interface():
    parser = _parser_top_traj(description='Analyse interfaces between any two groups of residues using a distance cutoff. '           
                                          'To help in the identification of these two groups of residues, '
                                          'the peptide-chain in the input topology '
                                          'can be automatically broken down into fragments and use them as input. '
                                          'The number of shown contacts depends on the parameters "n_ctcs" and '
                                          '"min_freq". ')

    _parser_add_fragments(parser)
    parser.add_argument("-fg1","--frag_idxs_group_1", type=str,
                        help="Indices of the fragments that belong to the group_1. "
                             "Defaults to None which will prompt the user of information, except when "
                             "only two fragments are present. Then it defaults to [0]", default=None)
    parser.add_argument("-fg2","--frag_idxs_group_2", type=str,
                        help="Indices of the fragments that belong to the group_2. "
                             "Defaults to None which will prompt the user of information, except when "
                             "only two fragments are present. Then it defaults to [1]", default=None)
    _parser_add_cutoff(parser)
    _parser_add_n_ctcs(parser, default=50)
    parser.add_argument("-mf", "--min_freq", type=float, default=.05,
                        help="Do not show frequencies smaller than this. If you notice the output being"
                             "truncated a values too far away from this, you need to increase the"
                             "'n_ctcs' parameter" )
    parser.add_argument("-ic", "--interface_cutoff_Ang", type=float,
                        help="The interface between both groups is defined as the set of group_1-group_2-"
                             "distances that are within this "
                             "cutoff in the reference topology. Otherwise, a large number of "
                             "non-necessary distances (e.g. between N-terminus and G-protein) are computed. Default is 35.",
                        default=35)
    _parser_add_n_neighbors(parser, default=0)
    _parser_add_stride(parser)
    _parser_add_smooth(parser)
    _parser_add_time_traces(parser)
    _parser_add_n_jobs(parser)
    _parser_add_fragment_names(parser)
    _parser_add_no_frag(parser)

    _parser_add_nomenclature(parser)
    _parser_add_chunk(parser)
    _parser_add_output_desc(parser,'interface')
    _parser_add_output_dir(parser)
    _parser_add_graphic_ext(parser)
    _parser_add_graphic_dpi(parser)
    _parser_add_curve_color(parser)
    _parser_add_t_unit(parser)
    _parser_add_gray_backgroud(parser)
    _parser_add_short_AA_names(parser)
    parser.add_argument('--sort_by_av_ctcs', dest='sort_by_av_ctcs', action='store_true',
                        help="When presenting the results summarized by residue, "
                             " sort by sum of frequencies (~average number of contacts)."
                             " Defaut is True.")
    parser.add_argument('--no-sort_by_av_ctcs', dest='sort_by_av_ctcs', action='store_false')
    parser.set_defaults(sort_by_av_ctcs=True)
    _parser_add_scheme(parser)
    _parser_add_pop(parser)
    _paser_add_guess(parser)
    _parser_add_title(parser)
    return parser

def parser_for_contact_map():
    parser = _parser_top_traj(description='Residue-residue contact-maps')

    parser.add_argument("--list_ctc_cutoff_Ang", type=str,
                        help="The cutoff distances between two residues for them to be considered in contact.",
                        default='3')
    _parser_add_stride(parser)
    _parser_add_n_jobs(parser)
    _parser_add_chunk(parser, default=100)
    _parser_add_output_desc(parser,'is_interface')
    _parser_add_output_dir(parser)
    _parser_add_graphic_ext(parser)
    _parser_add_graphic_dpi(parser)
    _parser_add_scheme(parser)

    return parser

def parser_for_frag_overview():
    parser = argparse.ArgumentParser(description='Break a molecular topology into fragments using different heuristics.')
    parser.add_argument('--methods', help='What methods to test. '
                                          'Default is all.',
                        nargs='+',
                        type=str,
                        default=['all']
                        )
    _parser_add_topology(parser)
    _parser_add_AAs(parser)
    return parser

def parser_for_BW_overview():
    parser = argparse.ArgumentParser(description='Map a Ballesteros-Weinstein (BW)-type '
                                                 'nomenclature on an input topology. '
                                                 'The BW nomenclature can be read locally or over the network')

    parser.add_argument("BW_uniprot_or_file", type=str,
                        help="Get Ballesteros-Weinstein definitions from here.\n"
                             "If a file is not found locally, look for\n"
                             " Ballesteros-Weinstein definitions in the GPRCmd\n"
                             "using this string as uniprot code, "
                             "e.g. adrb2_human. See https://gpcrdb.org/services/ for more details."
                        )
    parser.add_argument("-t",'--topology', type=str, help='Topology file', default=None)


    _parser_add_write_to_disk(parser)
    _parser_add_print_conlab(parser)
    _parser_add_fill_gaps(parser)
    _parser_add_AAs(parser)
    _parser_add_conslabels(parser)

    return parser

def parser_for_CGN_overview():
    parser = argparse.ArgumentParser(description="Map a Common G-alpha Numbering (CGN)-type nomenclature on an input topology. "
                                                 "The CGN nomenclature can be read locally or over the network" )

    parser.add_argument("-t", '--topology', type=str, help='Topology file', default=None)
    parser.add_argument("PDB_code_or_txtfile", type=str,
                        help="Get CGN definitions from here. If a file is not "
                             "found locally, there will be a web-lookup "
                             "in a database using a PDB code, "
                             "e.g. 3SN6. see www.mrc-lmb.cam.ac.uk")

    _parser_add_write_to_disk(parser)
    _parser_add_print_conlab(parser)
    _parser_add_fill_gaps(parser)
    _parser_add_AAs(parser)
    _parser_add_conslabels(parser)

    return parser

# TODO use the colorstring here?
def parser_for_compare_neighborhoods():
    parser = argparse.ArgumentParser(description="Compare residue-residue contact frequencies from different files.")
    parser.add_argument("files", type=str, nargs="+", help="Files (ASCII or .xlsx) containing the frequencies and labels in the first columns")
    parser.add_argument("-a","--anchor",type=str,default=None, help="A residue that appears in all contacts. It will be eliminated from the labels for clarity.")
    parser.add_argument("-k","--keys", type=str,default=None, help="The keys used to label the files, e.g. 'WT,MUT'")
    parser.add_argument("-c","--colors", type=str, default="tab:blue,tab:orange,tab:green,tab:red,tab:purple,tab:brown,tab:pink,tab:gray,tab:olive,tab:cyan")
    parser.add_argument("-m","--mutations",type=str, default=None,help='A replacement dictionary, to be able to re-label residues accross systems, e.g. "GLU:ARG,LYS:PHE" changes all GLUs to ARGs and all LYS to PHEs')
    _parser_add_output_desc(parser,"freq_comparison")
    _parser_add_graphic_ext(parser)
    return parser