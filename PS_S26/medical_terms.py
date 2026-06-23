# Set of medical terms for filtering

MEDICAL_KEYWORDS = {

    # Research terms
    "study", "cohort", "case-control", "cross-sectional", "prospective",
    "retrospective", "randomized", "placebo", "clinical trial",
    "meta-analysis", "systematic review", "hazard ratio",
    "odds ratio", "confidence interval", "multivariate",

    # Molecular biology
    "gene", "genome", "genomic", "transcriptome", "proteome",
    "epigenetic", "methylation", "transcription", "translation",
    "replication", "mutation", "variant", "allele", "haplotype",
    "polymorphism", "expression", "sequencing", "rna", "mrna",
    "mirna", "crispr", "polymerase", "ribosome",

    # Cell biology
    "cellular", "cytoplasm", "nucleus", "mitochondria",
    "endoplasmic reticulum", "golgi", "lysosome", "autophagy",
    "apoptosis", "necrosis", "proliferation", "differentiation",
    "signaling", "ligand", "receptor", "phosphorylation",

    # Immunology
    "immune", "immunology", "antigen", "antibody", "cytokine",
    "chemokine", "lymphocyte", "t cell", "b cell", "macrophage",
    "neutrophil", "dendritic", "interleukin", "interferon",
    "inflammation", "autoimmune",

    # Microbiology
    "bacterium", "bacterial", "virus", "viral", "virion",
    "fungal", "pathogen", "microbiome", "microbiota",
    "antimicrobial", "antibiotic", "resistance",

    # Pathology
    "pathogenesis", "etiology", "histopathology", "biopsy",
    "fibrosis", "ischemia", "hypoxia", "lesion",
    "malignancy", "metastasis", "tumorigenesis",

    # Clinical medicine
    "diagnosis", "prognosis", "comorbidity", "morbidity",
    "mortality", "prevalence", "incidence", "symptom",
    "syndrome", "therapy", "treatment", "intervention",

    # Pharmacology
    "pharmacokinetics", "pharmacodynamics", "bioavailability",
    "drug", "therapeutic", "toxicity", "cytotoxicity",
    "adverse event", "dose-response",

    # Laboratory methods
    "pcr", "qpcr", "western blot", "elisa", "flow cytometry",
    "immunohistochemistry", "microscopy", "spectrometry",
    "assay", "in vitro", "in vivo",

    # Anatomy & physiology
    "cardiovascular", "neurological", "hepatic", "renal",
    "pulmonary", "endocrine", "hematologic", "gastrointestinal",

    # Epidemiology & Biostatistics
    "covariate", "confounder", "stratification", "regression",
    "survival analysis", "censoring", "longitudinal", "endpoint",
    "outcome", "predictor", "association", "correlation",
    "incidence rate", "risk factor", "relative risk",
    "adjusted odds ratio", "sensitivity analysis",
    "specificity", "positive predictive value",
    "negative predictive value", "roc curve",
    "area under the curve", "a priori", "post hoc",

    # Clinical Research
    "double blind", "single blind", "open label",
    "randomization", "allocation", "follow-up",
    "participant", "enrollment", "intervention group",
    "control group", "baseline", "primary endpoint",
    "secondary endpoint", "adherence", "compliance",
    "screening", "eligibility", "exclusion criteria",
    "inclusion criteria", "adverse effect",

    # Molecular Biology
    "transcriptomic", "proteomic", "metabolomic",
    "epigenomic", "chromosome", "chromatin",
    "enhancer", "promoter", "exon", "intron",
    "spliceosome", "splicing", "transcript",
    "coding sequence", "open reading frame",
    "gene expression", "differential expression",
    "knockout", "knockdown", "overexpression",
    "wild type", "mutant", "genotyping",
    "whole genome sequencing", "rna-seq",
    "single-cell", "single-cell rna sequencing",

    # Cell Biology
    "organelle", "cytoskeleton", "microtubule",
    "actin", "tubulin", "membrane potential",
    "cell cycle", "cell signaling",
    "signal transduction", "cell adhesion",
    "extracellular matrix", "progenitor cell",
    "stem cell", "pluripotent", "multipotent",
    "differentiated", "cell lineage",
    "cell viability", "cell death",

    # Immunology
    "adaptive immunity", "innate immunity",
    "immune response", "immune activation",
    "immune suppression", "immune infiltration",
    "immune checkpoint", "toll-like receptor",
    "major histocompatibility complex",
    "mhc", "cd4", "cd8", "natural killer cell",
    "regulatory t cell", "monocyte",
    "eosinophil", "basophil", "immunoglobulin",
    "serology", "neutralizing antibody",
    "vaccination", "vaccine efficacy",

    # Microbiology & Infectious Disease
    "colonization", "biofilm", "bacteremia",
    "viremia", "fungemia", "pathogenicity",
    "virulence factor", "host-pathogen interaction",
    "microbial community", "commensal",
    "dysbiosis", "horizontal gene transfer",
    "antimicrobial resistance", "susceptibility testing",

    # Cancer Research
    "oncogene", "tumor suppressor",
    "tumor microenvironment", "neoplasm",
    "carcinoma", "sarcoma", "adenocarcinoma",
    "malignant", "benign", "proliferative",
    "invasive", "metastatic", "chemotherapy",
    "radiotherapy", "immunotherapy",
    "targeted therapy", "progression-free survival",

    # Pathology
    "histology", "pathology", "cytopathology",
    "immunostaining", "histological",
    "morphology", "cellular morphology",
    "biomarker discovery", "disease progression",
    "disease severity", "disease burden",

    # Pharmacology
    "therapeutic index", "drug metabolism",
    "drug interaction", "dose escalation",
    "maximum tolerated dose", "half-life",
    "clearance", "distribution volume",
    "efficacy", "potency", "bioequivalence",
    "pharmacogenomics", "drug target",

    # Laboratory Methods
    "immunoblot", "southern blot",
    "northern blot", "chromatography",
    "mass spectrometry", "electrophoresis",
    "confocal microscopy", "fluorescence microscopy",
    "next-generation sequencing", "ngs",
    "flow sorting", "cell sorting",
    "genome-wide association study",
    "gwas", "assay development",
    "high-throughput screening",

    # Physiology
    "homeostatic", "hemodynamics",
    "electrophysiology", "neurophysiology",
    "metabolic pathway", "signal pathway",
    "oxidative stress", "reactive oxygen species",
    "mitochondrial dysfunction", "energy metabolism",

    # Anatomy
    "myocardium", "endothelium", "epithelium",
    "parenchyma", "stroma", "hepatocyte",
    "nephron", "glomerulus", "alveolus",
    "axon", "dendrite", "synapse",
    "cortex", "medulla", "ventricle",

    # Common Biomedical Verbs
    "quantified", "characterized", "investigated",
    "validated", "evaluated", "assessed",
    "analyzed", "examined", "measured",
    "identified", "elucidated", "demonstrated",
    "observed", "compared", "correlated",
    "regulated", "mediated", "induced",
    "inhibited", "modulated", "expressed",

    # Common Biomedical Nouns
    "mechanism", "pathway", "cohort",
    "specimen", "sample", "subject",
    "participant", "dataset", "phenotyping",
    "genotyping", "strain", "isolate",
    "variant", "isoform", "construct",
    "vector", "clone", "culture",
    "replicate", "replication", "endpoint",

    # Cardiovascular
    "cardiac", "cardiovascular", "myocardial", "myocardium",
    "endocardial", "epicardial", "pericardial",
    "arterial", "venous", "vascular", "vasculature",
    "aortic", "aorta", "atrium", "ventricle",
    "capillary", "hemodynamic", "blood pressure",

    # Renal / Urinary
    "renal", "nephron", "nephritic", "nephrotic",
    "glomerular", "glomerulus", "tubular",
    "ureteral", "urethral", "bladder", "urogenital",
    "urinary", "diuresis", "proteinuria", "hematuria",

    # Gastrointestinal
    "gastric", "gastrointestinal", "enteric", "enterocyte",
    "intestinal", "duodenal", "jejunal", "ileal",
    "colonic", "colon", "rectal", "rectum",
    "esophageal", "esophagus", "hepatic portal",
    "digestive", "digestion", "gastroenterology",

    # Hepatic / Liver
    "hepatic", "hepatocyte", "liver", "biliary",
    "bile duct", "cholestasis", "cirrhosis",
    "hepatitis", "hepatobiliary",

    # Pulmonary / Respiratory
    "pulmonary", "respiratory", "alveolar", "alveolus",
    "bronchial", "bronchi", "bronchiole",
    "tracheal", "trachea", "pleural", "pleura",
    "lung", "ventilation", "gas exchange",
    "hypoxemia", "hypercapnia",

    # Neurological / Nervous System
    "neurological", "neural", "neuronal", "neuron",
    "axon", "dendrite", "synaptic", "synapse",
    "cerebral", "cerebellar", "cortex",
    "spinal", "spinal cord", "brainstem",
    "hippocampal", "glial", "gliosis",

    # Endocrine
    "endocrine", "hormonal", "hormone",
    "thyroid", "parathyroid", "pituitary",
    "adrenal", "pancreatic", "insulin",
    "glucagon", "cortisol", "estrogen",
    "testosterone",

    # Musculoskeletal
    "musculoskeletal", "muscle", "myocyte",
    "skeletal", "bone", "osseous",
    "cartilage", "tendon", "ligament",
    "osteoblast", "osteoclast", "osteocyte",
    "arthritis", "arthritic",

    # Hematologic / Blood
    "hematologic", "hematopoietic", "erythrocyte",
    "leukocyte", "thrombocyte", "platelet",
    "hemoglobin", "anemia", "coagulation",
    "clotting", "fibrin", "plasma", "serum",

    # Skin / Integumentary
    "dermal", "dermatologic", "epidermal",
    "epidermis", "dermis", "cutaneous",
    "skin", "melanocyte", "keratinocyte",
    "wound healing", "scar formation",

    # Reproductive
    "reproductive", "gonadal", "ovarian",
    "testicular", "uterine", "placental",
    "embryonic", "fetal", "gestational",
    "oocyte", "sperm", "zygote",

    # General organ-level pathology terms
    "organ dysfunction", "organ failure",
    "multi-organ", "systemic", "physiologic",
    "pathophysiologic", "homeostasis",
    "inflammation", "ischemia", "hypoxia",
    "necrosis", "fibrosis", "atrophy", "hypertrophy",

    "medicine"
}
