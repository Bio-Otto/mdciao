from setuptools import setup, find_packages

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

test_deps = [
    'coverage',
    'pytest',
    'nose',
    "mock"
]

doc_deps = [
    "sphinx",
    "sphinx-argparse",
    "sphinx-rtd-theme"
]

setup(
    name="mdciao",
    version="0.0.1.rc2",
    author_email="guillermo.perez@charite.de",
    description="mdciao: Analysis of Molecular Dynamics Simulations Using Residue Neighborhoods",
    url="https://github.com/gph82/mdciao",
    project_urls={
        "docs": "http://proteinformatics.org/mdciao",
    },
    python_requires=">=3.6",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    packages=find_packages(),
    install_requires=[
                    "cython",
                    "numpy>=1.18.1",
                    "mdtraj",
                    "astunparse; python_version!='3.8'",
                    "astunparse<1.6.3; python_version=='3.8'",
                    "pandas",
                    "matplotlib",
                    "msmtools",
                    "scipy",
                    "joblib",
                    "openpyxl",
                    "biopython",
                    "ipython",
                    "XlsxWriter",
                    "requests",
                    "tqdm",
                    "natsort",
                    "bezier",
                     ]
                     +test_deps
                     #+doc_deps
    # tests_require=test_deps, # has been deprecated, gotta learn how to use tox
    ,
    data_files=[
        ('tests/data/examples', ['tests/data/examples/gs-b2ar.noH.stride.5.xtc']),
        ('tests/data/examples', ['tests/data/examples/gs-b2ar.noH.pdb']),
        ('tests/data/nomenclature', ['tests/data/nomenclature/adrb2_human.xlsx']),
        ('tests/data/nomenclature', ['tests/data/nomenclature/CGN_3SN6.txt']),
        ('tests/data/json', ['tests/data/json/tip.json']),
        ('tests/data/RSCB_pdb', ['tests/data/RSCB_pdb/3SN6.pdb.gz']),
    ],
    scripts=['scripts/mdc_neighborhoods.py',
             'scripts/mdc_sites.py',
             'scripts/mdc_interface.py',
             'scripts/mdc_fragments.py',
             'scripts/mdc_BW_overview.py',
             'scripts/mdc_CGN_overview.py',
             'scripts/mdc_compare.py',
             'scripts/mdc_examples.py',
             'scripts/mdc_pdb.py',
             'scripts/mdc_residues.py',
             #'scripts/density_by_sites.py',
             #'scripts/site_figures.py',
             #'scripts/residue_dihedrals.py',
             #'scripts/contact_maps.py'
             #'scripts/CARDS.py'
             ],
)

