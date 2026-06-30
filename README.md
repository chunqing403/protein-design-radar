# Protein Design Paper Radar

Daily frontier papers for deep learning-based protein design, protein engineering, and biomolecular modeling.

This repository is inspired by curated paper lists such as `Peldom/papers_for_protein_design_using_DL`, but is designed to update itself every day. The newest recommended papers are written directly into this README.

<!-- PAPER_RADAR:START -->
## Latest Recommendations

Updated: **2026-06-30** (`2026-06-30T03:45:19Z`)

| # | Paper | Source | Topics | Score |
|---|---|---|---|---:|
| 1 | [Multi-dimensional orchestration of binders for improved CAR-T immunotherapy.](https://pubmed.ncbi.nlm.nih.gov/42365891/)<br><sub>Zhu C, Jiang Z, Jing R et al.</sub> | PubMed<br>2026 Jun 28 | Binders and therapeutics | 9 |

### By Topic

#### Binders and therapeutics

- [Multi-dimensional orchestration of binders for improved CAR-T immunotherapy.](https://pubmed.ncbi.nlm.nih.gov/42365891/) (PubMed, 2026 Jun 28)

### Archive

- [Daily report for 2026-06-30](outputs/daily/2026-06-30.md)
- [Latest report](outputs/latest.md)

<!-- PAPER_RADAR:END -->

## Databases and Resources

### Protein Sequence and Annotation

| Resource | Type | Use |
|---|---|---|
| [UniProt](https://www.uniprot.org/) | Sequence / annotation | Curated protein sequences, functions, domains, variants, proteomes |
| [NCBI Protein](https://www.ncbi.nlm.nih.gov/protein/) | Sequence | Protein records linked to GenBank, RefSeq, structures, literature |
| [InterPro](https://www.ebi.ac.uk/interpro/) | Family / domain | Protein families, domains, repeats, signatures |
| [Pfam](https://www.ebi.ac.uk/interpro/entry/pfam/) | Domain family | HMM-based protein domain families, now served through InterPro |
| [MGnify](https://www.ebi.ac.uk/metagenomics/) | Metagenomics | Large-scale microbiome protein and genome annotations |

### Structure and Fold Space

| Resource | Type | Use |
|---|---|---|
| [RCSB PDB](https://www.rcsb.org/) | Experimental structure | X-ray, cryo-EM, NMR structures of proteins and complexes |
| [wwPDB](https://www.wwpdb.org/) | Structure archive | Global archive for experimentally determined macromolecular structures |
| [AlphaFold DB](https://alphafold.ebi.ac.uk/) | Predicted structure | AlphaFold-predicted structures for large-scale proteomes |
| [ESM Metagenomic Atlas](https://esmatlas.com/) | Predicted structure | Predicted structures for metagenomic proteins |
| [CATH](https://www.cathdb.info/) | Fold classification | Hierarchical classification of protein domains and superfamilies |
| [SCOPe](https://scop.berkeley.edu/) | Fold classification | Expert-curated structural classification of proteins |
| [ECOD](http://prodata.swmed.edu/ecod/) | Evolutionary domains | Evolutionary classification of protein domains |

### Function, Enzymes, and Pathways

| Resource | Type | Use |
|---|---|---|
| [BRENDA](https://www.brenda-enzymes.org/) | Enzyme database | Enzyme function, kinetics, substrates, inhibitors, organisms |
| [KEGG](https://www.kegg.jp/) | Pathway / metabolism | Pathways, reactions, compounds, genes, enzyme context |
| [Reactome](https://reactome.org/) | Pathway | Curated biological pathways and reactions |
| [MetaCyc](https://metacyc.org/) | Metabolic pathways | Experimentally supported metabolic pathways and enzymes |
| [CAZy](https://www.cazy.org/) | Carbohydrate enzymes | Glycoside hydrolases, transferases, lyases, esterases |
| [M-CSA](https://www.ebi.ac.uk/thornton-srv/m-csa/) | Catalytic mechanism | Enzyme catalytic sites and reaction mechanisms |

### Binding, Interaction, and Complexes

| Resource | Type | Use |
|---|---|---|
| [STRING](https://string-db.org/) | Protein association | Known and predicted protein-protein association networks |
| [BioGRID](https://thebiogrid.org/) | Interaction | Curated genetic and protein interaction data |
| [IntAct](https://www.ebi.ac.uk/intact/) | Molecular interaction | Curated molecular interaction evidence |
| [PDBbind](http://www.pdbbind.org.cn/) | Binding affinity | Protein-ligand complexes with binding affinity data |
| [BindingDB](https://www.bindingdb.org/) | Binding affinity | Protein-small molecule binding measurements |
| [SKEMPI](https://life.bsc.es/pid/skempi2/) | Mutant binding | Effects of mutations on protein-protein binding energetics |

### Variants, Mutational Effects, and Fitness

| Resource | Type | Use |
|---|---|---|
| [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) | Clinical variants | Variant-phenotype and clinical significance annotations |
| [gnomAD](https://gnomad.broadinstitute.org/) | Population variants | Human genetic variation and allele frequencies |
| [MaveDB](https://www.mavedb.org/) | Multiplex assays | Deep mutational scanning and multiplexed variant effect datasets |
| [ProteinGym](https://proteingym.org/) | Benchmark | DMS-based benchmarks for protein sequence models |
| [FLIP](https://benchmark.protein.properties/) | Benchmark | Protein fitness landscape prediction benchmarks |

### Design Models, Datasets, and Benchmarks

| Resource | Type | Use |
|---|---|---|
| [ProteinMPNN](https://github.com/dauparas/ProteinMPNN) | Inverse folding | Sequence design for fixed protein backbones |
| [RFdiffusion](https://github.com/RosettaCommons/RFdiffusion) | Generative design | Diffusion-based protein backbone and binder design |
| [ColabDesign](https://github.com/sokrypton/ColabDesign) | Design toolkit | AlphaFold-guided hallucination, binder design, sequence design |
| [ESM](https://github.com/facebookresearch/esm) | Protein language model | Protein language models and structure prediction tools |
| [OpenProteinSet](https://github.com/google-research/proteinfer/tree/main/open_protein_set) | Training data | Large-scale protein sequence set for ML pretraining |
| [TAPE](https://github.com/songlab-cal/tape) | Benchmark | Tasks for evaluating protein sequence models |
