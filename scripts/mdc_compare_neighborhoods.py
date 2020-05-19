#!/home/perezheg/miniconda3/bin/python
from mdciao.parsers import parser_for_compare_neighborhoods
from mdciao.command_line_tools import neighborhood_comparison
from matplotlib import pyplot as plt

# Get and instantiate parser
parser = parser_for_compare_neighborhoods()
a  = parser.parse_args()
nf = len(a.files)
if a.keys is None:
   keys = ["file %u"%ii for ii in range(nf)]
else:
    assert len(a.keys.split(","))==nf
    keys = a.keys.split(",")
print(a.files)
print(a.anchor,type(a.anchor))
file_dict = {key: file for key, file in zip(keys, a.files)}
col_dict =  {key: col for key, col in zip(keys, a.colors.split(","))}
mut_dict = {}
if a.mutations is not None:
    for pair in a.mutations.split(","):
        key, val = pair.split(":")
        mut_dict[key.replace(" ","")]=val.replace(" ","")

# Call the method
myfig, freqs, posret = neighborhood_comparison(file_dict, col_dict,
                                               anchor=a.anchor,
                                               mutations_dict=mut_dict)
plt.show()

