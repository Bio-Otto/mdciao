#!/home/perezheg/miniconda3/bin/python
import numpy as np
from mdciao.parsers import _paser_of_cn
from mdciao.command_line_tools import neighborhood_comparison

# Get and instantiate parser
parser = _paser_of_cn()
a  = parser.parse_args()
assert len(a.keys.split(","))==len(a.files.split(","))
file_dict = {key: file for key, file in zip(a.keys.split(","), a.files.split(","))}
col_dict =  {key: col for key, col in zip(a.keys.split(","), a.colors.split(","))}
mut_dict = {}
for pair in a.mutations.split(","):
    key, val = pair.split(":")
    mut_dict[key.replace(" ","")]=val.replace(" ","")
print(file_dict)
print(col_dict)
print(mut_dict)

# Call the method
ifig = neighborhood_comparison(file_dict, a.anchor, col_dict, mutations=mut_dict)
ifig.savefig("comp.png")

