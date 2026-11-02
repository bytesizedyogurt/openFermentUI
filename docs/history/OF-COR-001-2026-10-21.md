# openFerment Corpus v1.0 — Real Literature for the cw15 → β-Casein Program

**Document:** OF-COR-001 · **Version:** 1.0 · **Date:** 2026-08-10
**Companion to:** OF-DES-001 v0.1

Replaces the synthetic demo corpus of OF-DES-001 §14 with a real, curated
literature base for expression of phosphorylated bovine β-casein in the
cell-wall-deficient *Chlamydomonas reinhardtii* strain cw15 and its UVM
derivatives, for animal-free dairy applications.

**[verify]** marks entries with confirmed title/journal/year/DOI but author
strings not fully resolved. The DOI or PMCID is the authoritative key — never
the author string.

## 0. Why this program

**Caseins have been expressed in bacteria, in yeast, and in plants. They have
never been published in a microalga.** Mora Vásquez et al. (2025) tabulate
every reported attempt — 17 bacterial, 5 yeast, 2 plant studies — and there is
no algal row. The only algal mention is a patent application (Kiverdi,
WO2024015365A1) listing algae generically among possible hosts.

The case for cw15 assembles from four established facts:

1. **A real secretory pathway.** Unlike *E. coli*, cw15 derivatives route
   proteins through ER and Golgi, cleave signal peptides, and N-glycosylate.
   Secretion from UVM4 is established at 12–15 mg/L.
2. **GRAS status.** *C. reinhardtii* is among a short list of microalgae with
   FDA GRAS status for human consumption.
3. **Cell wall deficiency is a downstream asset.** Wall-deficient microalgae
   release protein at ~3× the yield of walled strains under pulsed electric
   field, at mild conditions.
4. **The hard problem is the same everywhere.** Phosphorylation at Ser-x-Glu
   motifs by FAM20C is what makes casein assemble, bind calcium, and coagulate.
   No yeast, plant, or bacterial host does this natively for bovine β-casein.

The honest counterweight: nuclear transgene expression in *Chlamydomonas* is
historically weak (~0.2% TSP for intracellular reporters), secreted yields are
two to three orders below *Trichoderma* β-lactoglobulin (1 g/L), and the UVM4
secretome is clogged with unassembled cell wall glycoprotein aggregates that
make secreted-product purification genuinely hard. A platform built on this
host is a research bet, not an engineering exercise.

**Consequence for OF-DES-001:** the honesty policy in §20 changes character.
Papers, authors, values and spans are now real, so demo labelling collapses to
two remaining synthetic surfaces — the simulation response grids (§17) and
scripted agent answer text. Extraction errors are now errors about real papers.

## 1. Corpus map

| Thread | Subject | Entries |
|---|---|---|
| A | Host platform: cw15, UVM4/UVM11, transformation, silencing | 9 |
| B | Expression optimization: codon usage, introns, promoters, terminators | 5 |
| C | Localization: intracellular vs secretion, signal peptides, secretome | 9 |
| D | Host PTM capability: N-glycosylation, the FAM20C question | 5 |
| E | The molecule: β-casein structure, disorder, micelle assembly | 9 |
| F | The gene: CSN2, variants, A1/A2, phospho-site positions | 5 |
| G | FAM20C biology: identity, motif, structure, regulation | 9 |
| H | Phosphorylation in heterologous hosts: what has been achieved | 16 |
| I | Functionality: does phosphorylation matter, and how much | 9 |
| J | Purification and downstream processing | 11 |
| K | Comparable successes in other hosts | 10 |
| L | Products: plant-based cheese/yogurt gaps | 8 |
| M | Cultivation: cw15 growth, TAP, mixotrophy | 8 |
| N | Food safety and regulatory | 4 |
| O | TEA and process modeling | 8 |

**Total: 125 entries.**

## 2. Thread A — Host platform: cw15 and its derivatives

**A1. Neupert J, Karcher D, Bock R (2009).** Generation of *Chlamydomonas* strains that efficiently express nuclear transgenes. *Plant J* 57(6):1140–1150. DOI 10.1111/j.1365-313X.2008.03746.x
The foundational strain paper. Arginine-auxotrophic cell-wall-deficient cw15-302 (= CC-4350, cwd mt+ arg7) was co-transformed with the CRY1-1 emetine resistance gene and ARG7 to give Elow47; UV mutagenesis of Elow47 followed by selection for high transgene expression yielded UVM4 and UVM11. Both reach ~0.2% of total soluble protein for intracellular GFP/YFP. Selection used paromomycin at 10 µg/mL and zeocin.

**A2. Neupert J, et al. (2020).** An epigenetic gene silencing pathway selectively acting on transgenic DNA in the green alga *Chlamydomonas*. *Nat Commun* 11:6269. DOI 10.1038/s41467-020-19983-4
Identifies the causative lesion in UVM4/UVM11 as a Sir2-type histone deacetylase (SRTA). ChIP against H3K9/K14ac and H4K5ac establishes the chromatin mechanism. Untransformed CC-4350 and Elow47 show no detectable YFP. If the mechanism is silencing relief rather than a transcription gain, a two-gene construct inherits the same benefit — an argument that needs testing.

**A3. Barahimipour R, Neupert J, Bock R (2016).** Efficient expression of nuclear transgenes in the green alga *Chlamydomonas*: synthesis of an HIV antigen and development of a new selectable marker. *Plant Mol Biol* 90:403–418. PMC4766212
Case study on expressing a non-reporter, biotechnologically relevant protein (HIV capsid P24) plus rescue of nptII as a marker. The closest published analogue to what a CSN2 construct would have to do.

**A4. Zhang MP, Wang M, Wang C (2021).** Nuclear transformation of *Chlamydomonas reinhardtii*: A review. *Biochimie* 181:1–11. PMID 33227342
Systematic review of transformation methods, selection genes, and efficiency factors. Integration proceeds by non-homologous end joining at random loci; homologous recombination occurs at much lower frequency; insertional events can cause deletion, recombination, or translocation near the integration site.

**A5. Molecular Advancements Establishing *Chlamydomonas* as a Host for Biotechnological Exploitation.** PMC9277225, ~2022. **[verify]**
Covers the UVM4/UVM11 mating limitation — the strains can hardly be crossed, so each transgene must be introduced by separate transformation with a distinct marker. Notes a walled, mating-competent UVM11 derivative. A two-cassette CSN2 + FAM20C program is exactly the case this limitation bites.

**A6. Current Nuclear Engineering Strategies in the Green Microalga *Chlamydomonas reinhardtii*.** PMC10381326. **[verify]**
Consolidates NHEJ integration behavior, position-effect variance across transformants, the SRTA and *met1* silencing routes, and CRISPR editing status.

**A7. Transcriptional gene fusions via targeted integration at safe harbors for high transgene expression in *Chlamydomonas reinhardtii*.** PMC12371178. **[verify]**
Identifies the LHCBM1 locus as a genetic safe harbor; reports an 8.6-fold increase in transgenic protein accumulation over random insertion, and a 60-fold increase in valencene production when a sesquiterpene synthase was co-expressed there. The single most actionable expression-boost result in the thread.

**A8. *Chlamydomonas reinhardtii* as a viable platform for the production of recombinant proteins: current status and perspectives.** *Plant Cell Rep* (2011). DOI 10.1007/s00299-011-1186-8; PMID 22080228. **[verify]**
Enumerates the factors limiting expression — enhancer elements, codon dependency, protease sensitivity, transformation-associated genotypic modification.

**A9. *Chlamydomonas reinhardtii*: a protein expression system for pharmaceutical and biotechnological proteins.** PMID 17172667 (2007). **[verify]**
Earlier platform review; useful for the historical arc before UVM4.

## 3. Thread B — Expression optimization

**B1. Barahimipour R, Strenkert D, Neupert J, Schroda M, Merchant SS, Bock R (2015).** Dissecting the contributions of GC content and codon usage to gene expression in the model alga *Chlamydomonas reinhardtii*. *Plant J* 84:704–717. DOI 10.1111/tpj.13033; PMC4715772
The decisive experiment: YFP variants encoding identical amino acid sequences but differing in GC content and/or codon usage. Codon usage is the key determinant of translational efficiency and, unexpectedly, of mRNA stability; unfavorable GC content acts at the chromatin level by triggering heterochromatinization. High-expressing mutant strains are less susceptible to epigenetic suppression. β-casein is proline-rich and mammalian-codon-biased — the exact case this paper predicts will fail without resynthesis.

**B2. Intron-containing algal transgenes mediate efficient recombinant gene expression in the green microalga *Chlamydomonas reinhardtii*.** *Nucleic Acids Res* (2018) 46(13):6909. **[verify]**
Establishes sequence-specific dynamics of native intron insertion into nuclear transgenes. Records the nuclear genome at ~64% GC overall and ~68% in coding regions with narrow codon bias, and notes that most robust engineering reports involve short reporter CDSs rather than long cargo. Mature β-casein CDS is 627 nt.

**B3. Weiner I, Atar S, Schweitzer S, Eilenberg H, Feldman Y, Avitan M, et al. (2018).** Enhancing heterologous expression in *Chlamydomonas reinhardtii* by transcript sequence optimization. *Plant J* 94:22–31. PMID 29383789

**B4. Introns mediate post-transcriptional enhancement of nuclear gene expression in the green microalga *Chlamydomonas reinhardtii*.** *PLOS Genet* (2020) 16(7):e1008944. **[verify]**

**B5. Exploring the Impact of Terminators on Transgene Expression in *Chlamydomonas reinhardtii* with a Synthetic Biology Approach.** *Life* (2021) 11(9):964. DOI 10.3390/life11090964; PMC8471596. **[verify]**
Nine terminators across three size classes tested against a GFP reporter; optimal size tracked the median terminator length in the genome; PSAD and CA1 terminators gave significantly higher transformant counts than a no-3′UTR control (p<0.01). Directly compares transformation of cw15, UVM4, and walled WT12: colonies appear on selection in 7–10 days for cw15 and UVM4 versus 15–20 days for WT12. States the trade-off plainly — cell-wall-deficient strains have reduced motility and mating ability and are much more susceptible to shear and osmotic stress. The shear sensitivity is a bioreactor design constraint that propagates into the Simulate module's agitation and scale assumptions.

## 4. Thread C — Localization: intracellular versus secretion

**C1. Lauersen KJ, Berger H, Mussgnug JH, Kruse O (2013).** Efficient recombinant protein production and secretion from nuclear transgenes in *Chlamydomonas reinhardtii*. *J Biotechnol* 167(2):101–110. DOI 10.1016/j.jbiotec.2012.10.010; PMID 23099045
Establishes the CAH1 (carbonic anhydrase 1) signal peptide for heterologous secretion.

**C2. Ramos-Martinez EM, Fimognari L, Sakuragi Y (2017).** High-yield secretion of recombinant proteins from the microalga *Chlamydomonas reinhardtii*. *Plant Biotechnol J*. DOI 10.1111/pbi.12710; PMC5552477
The current secretion benchmark. The putative gametolysin signal sequence directs Venus into the medium; C-terminal fusion to synthetic glycomodules of tandem Ser-Pro repeats — (SP)10 and (SP)20 — raised yields up to 12-fold, reaching a maximum of 15 mg/L, and conferred enhanced proteolytic stability. The number every openFerment secretion scenario is measured against, and the number that makes the honest case that algal secretion is currently ~65× below *Trichoderma* β-lactoglobulin.

**C3. Molino JVD, et al. (2018).** Comparison of secretory signal peptides for heterologous protein expression in microalgae. *PLoS ONE*. PMC5800701
Ten signal peptides evaluated, drawn from four classes of natively secreted protein: BiP1, ARS1, CAH1, and IBP1, plus newly identified sequences from unexplored regions of the genome — two of which outperformed the established set. The decision table for which SP to fuse to CSN2.

**C4. Rasala BA, et al. (2012).** Robust Expression and Secretion of Xylanase1 in *Chlamydomonas reinhardtii* by Fusion to a Selection Gene and Processing with the FMDV 2A Peptide. *PLoS ONE* 7(8):e43349. PMC3427385
Xylanase linked directly to an antibiotic resistance gene via the FMDV self-cleaving 2A sequence. LC-MS/MS confirms the ARS1 signal peptide is correctly cleaved during ER transit — peptides covering 97% of the cytoplasmic and 89% of the secreted sequence were identified, with no ARS1 peptides detected. The 2A strategy is the most direct published answer to A5's two-cassette problem: a single transcript could carry CSN2-2A-FAM20C.

**C5. Eichler-Stahlberg A, Weisheit W, Ruecker O, Heitzer M (2009).** Strategies to facilitate transgene expression in *Chlamydomonas reinhardtii*. *Planta*. **[verify]**
Source of the ARS2 signal peptide approach.

**C6. Unassembled cell wall proteins form aggregates in the extracellular space of *Chlamydomonas reinhardtii* strain UVM4.** *Appl Microbiol Biotechnol* (2022) 106. DOI 10.1007/s00253-022-11960-9; PMC9200674. **[verify]**
The most important cautionary paper in the corpus. Compares the extracellular proteome of UVM4 to its walled ancestor 137c under matched conditions. UVM4 produces a distinct extracellular proteomic profile with higher abundance of secreted cell wall glycoproteins; secreted recombinant proteins become trapped in a matrix of these aggregates, making isolation and purification difficult. Recites the yield history: 0.2% TSP intracellular (Neupert 2009) → 12–15 mg/L secreted (Lauersen 2013; Ramos-Martinez 2017). NOTE: its 12–15 mg/L is a citation of C2, not an independent measurement.

**C7. Towards a biotechnological platform for the production of human pro-angiogenic growth factors in the green alga *Chlamydomonas reinhardtii* (2020).** **[verify]**
Working example of the full secretion architecture in UVM4/UVM11: the 21-amino-acid leader peptide of arylsulfatase ARS2 (Cre16.g671350, Phytozome v5.5) inserted upstream of the coding sequence, with APHVIII for selection, expressing VEGF-165. The construct template a CSN2 secretion cassette would be modeled on.

**C8. Efficient secretory production of recombinant proteins in microalgae using an exogenous signal peptide.** *Front Microbiol* (2025) 16:1603204. **[verify]**
Novel SP from a ~17 kDa highly secreted protein in *Chlorella* sp. HS2; demonstrates non-native signal sequences can work in microalgae. Carries a consolidated table of SPs used in *C. reinhardtii*: FEA1, ARS1/ARS2, CAH1, BiP1, gametolysin.

**C9. Comparing the Ability of Secretory Signal Peptides for Heterologous Expression of Anti-Lipopolysaccharide Factor 3 in *Chlamydomonas reinhardtii* (2023).** PMID 37367671

## 5. Thread D — Host post-translational modification capability

**D1. Mathieu-Rivet E, et al. (2013).** Exploring the N-glycosylation Pathway in *Chlamydomonas reinhardtii* Unravels Novel Complex Structures. *Mol Cell Proteomics* 12(11):3160–3183. PMC3820931
Endogenous soluble and membrane-bound proteins carry predominantly oligomannosides from Man-2 to Man-5; oligomannosidic N-glycans account for nearly 70% of the total N-glycan population; minor complex N-glycans are partially 6-O-methylated Man-3 to Man-5 bearing one or two xylose residues. β-casein is not natively N-glycosylated, so algal N-glycosylation is a risk rather than a requirement.

**D2. Heterologous expression of the N-acetylglucosaminyltransferase I dictates a reinvestigation of the N-glycosylation pathway in *Chlamydomonas reinhardtii* (2017).** *Sci Rep* 7. DOI 10.1038/s41598-017-10698-z; PMC5578997. **[verify]**
*C. reinhardtii* proteins carry a linear Man5GlcNAc2 rather than the branched eukaryotic structure, arising from a Glc3Man5GlcNAc2 precursor and GnTI-independent Golgi processing. Complementation with Arabidopsis or *Phaeodactylum* GnTI produced no glycan change but did produce a stress phenotype: enlarged vacuoles, increased ROS, starch accumulation — read as Golgi perturbation. A direct warning that forcing mammalian-type Golgi machinery into this host has produced cellular stress before.

**D3. Altered N-glycan composition impacts flagella-mediated adhesion in *Chlamydomonas reinhardtii* (2020).** *eLife* 9:e58805. **[verify]**
Insertional and CRISPR knockouts of xylosyltransferase 1A; establishes tools for manipulating algal N-glycan composition.

**D4. Green algae *Chlamydomonas reinhardtii* possess endogenous sialylated N-glycans (2011).** **[verify]**
Mass spectrometry of released N-linked oligosaccharides reports mammalian-like sialylated N-glycans in total extracts. CONFLICT: this contradicts D1 and D2, which describe an oligomannosidic, xylose-decorated, GnTI-independent pathway with no sialylation. Deliberately retained as a conflict case — the agent must surface the disagreement rather than average it.

**D5. The FAM20C-in-algae gap — OPEN.**
No retrieved source establishes whether *C. reinhardtii* possesses a Fam20-family secretory kinase. Evidence is indirect and points toward absence: Fam20 kinases are described as conserved across the animal kingdom from sponges to mammals, and plants do not express FAM20C and have never successfully phosphorylated recombinant caseins with endogenous machinery. *Chlamydomonas* sits outside the animal lineage. ACTION: HMM search of the *C. reinhardtii* v6.1 proteome against Pfam PF03881, plus a search of the algal secretory-pathway kinase literature. The canonical known-unknown — a demonstration that the platform records what the literature does not say.

## 6. Thread E — The molecule: β-casein structure and assembly

**E1. Atamer Z, Post AE, Schubert T, Holder A, Boom RM, Hinrichs J (2017).** Bovine β-casein: Isolation, properties and functionality. A review. *Int Dairy J* 66:115–125. DOI 10.1016/j.idairyj.2016.11.010
Casein is ~80% of total bovine milk protein; β-casein is present at roughly 2.6 g/L; caseins are heat-stable but precipitate readily at their isoelectric point, pH 4.65, on acidification. Reviews fractionation technologies at technical scale. The single most useful reference-value source in the thread.

**E2. Horvath A, et al. (2022).** Are casein micelles extracellular condensates formed by liquid–liquid phase separation? *FEBS Lett*. DOI 10.1002/1873-3468.14449
Native casein micelle geometry: approximately spherical, radius ~70 nm, containing on the order of 10,000 casein molecules, with caseins bound to amorphous calcium phosphate nanoclusters and retaining hydration and conformational flexibility upon self-assembly. The target specification.

**E3. Portnaya I, et al. (2006).** Micellization of bovine β-casein. *J Agric Food Chem* 54:5555–5561.
209 amino acids; molecular mass 23,946–24,097 Da depending on genetic variant; the most hydrophobic casein by virtue of a large hydrophobic C-terminal domain, but strongly amphipathic because of a highly charged N-terminal domain carrying the phosphate center; self-assembles into micelles of roughly 15–60 molecules with a critical micelle concentration around 0.05–0.2% depending on temperature, pH, solvent composition and ionic strength.

**E4. Farrell HM Jr, et al. (2004).** Nomenclature of the proteins of cows' milk — sixth revision. *J Dairy Sci* 87:1641–1674. The naming and variant authority.

**E5. Holt C, Carver JA, Ecroyd H, Thorn DC (2013).** Caseins and the casein micelle: their biological functions, structures, and behavior in foods. *J Dairy Sci* 96:6127–6146.

**E6. Manguy J, Shields DC (2019).** Implications of kappa-casein evolutionary diversity for the self-assembly and aggregation of casein micelles. *R Soc Open Sci* 6:190939. DOI 10.1098/rsos.190939; PMC6837221
Caseins in a micelle are substantially disordered — no fixed structure, free movement while the micelle keeps overall shape. α- and β-caseins sit mostly inside and bind calcium phosphate; κ-casein sits mostly at the surface. Alone at high concentration, caseins can form insoluble amyloid fibrils, and calcium at milk concentrations would precipitate; micelle formation prevents both.

**E7. de Kruif CG, Huppertz T, et al. (2012).** Aggregation Behavior of Bovine κ- and β-Casein Studied with SANS, Light Scattering, and Cryo-TEM. *Langmuir* 28. DOI 10.1021/la302416p
κ-casein forms amyloid-like fibrils at 25 °C under agitation; β-casein inhibits that fibrillation. Calcium-sensitive caseins sequester amorphous calcium phosphate in nanometer clusters while calcium-insensitive κ-casein limits micelle growth.

**E8. Self-Assembly of Bovine β-Casein below the Isoelectric pH.** *J Agric Food Chem*. DOI 10.1021/jf072630r. **[verify]**
SAXS below the CMC indicates the monomer is in a premolten globule state at low pH; net charge is similarly high at acidic and neutral pH but charge distribution along the backbone differs considerably, producing disk micelles above the CMC at low pH.

**E9. Structural and dynamic characterization of intrinsically disordered β-casein. [verify]**
*Nanosecond structural dynamics of intrinsically disordered β-casein micelles by neutron spectroscopy* (*Biophys J*, 2021) — self-association does not reduce monomer chain flexibility. *Self-assembly and secondary structure of beta-casein* (*Russ J Bioorg Chem*, 2013) — micellization involves few residues in transition and is not driven by a large secondary-structure change. Because β-casein is intrinsically disordered, the usual recombinant-protein success criterion (correct fold) does not apply; the criterion is correct phosphorylation and assembly behavior.

## 7. Thread F — The gene: CSN2

**F1. Cieślińska A, Fiedorowicz E, Rozmus D, Sienkiewicz-Szłapka E, Jarmołowska B, Kamiński S (2022).** Does a Little Difference Make a Big Difference? Bovine β-Casein A1 and A2 Variants and Human Health — An Update. *Int J Mol Sci* 23:15637. DOI 10.3390/ijms232415637; PMC9779325
Bovine CSN2 spans 10,338 bp on chromosome 6, comprises nine exons and eight introns (GenBank M55158.1). The primary translation product is 224 amino acids (GenBank AAA30431.1) including a signal peptide removed during processing, giving a 209-residue mature protein. Fifteen coding-region variants are reported; most mutations fall in exon 7; variants classify as A2-type (10 variants, Pro67) or A1-type (5 variants, His67) by a single SNP at codon 67. Design consequence: the native 15-residue bovine signal peptide must be removed and replaced with an algal SP.

**F2. A1/A2 variant selection evidence. [verify]**
The A1/A2 difference is a proline→histidine substitution at position 67 from a single nucleotide change; A2 is ancestral and A1 derived, with A1 at highest frequency in modern Holstein-Friesians; proteolytic cleavage at position 67 in A1 releases the seven-residue opioid peptide β-casomorphin-7 (Tyr-Pro-Phe-Pro-Gly-Pro-Ile), which A2 does not release. A1 is reported to improve curd consistency, milk coagulation, and micelle size relative to A2 — so choosing A2 is a marketing-and-health-positioning decision that costs cheesemaking performance. Sources: bioRxiv 2022 DOI 10.1101/2022.08.25.505361; PMC7070732; PMC12285589.

**F3. Frequency of β-Casein Gene Polymorphisms in Jersey Cows in Western Japan.** PMC9404981. **[verify]**
Records that 35 of the 209 residues in the A2 variant are proline — a cyclic residue that complicates secondary structure formation, and the structural reason digestive enzymes cannot cleave at position 67 when proline is present. Proline content this high is a codon-optimization problem in a 68%-GC-coding-region host.

**F4. Associations Between Polymorphisms of the CSN1S1, CSN1S2, CSN2 and CSN3 Genes and Milk Composition Traits in Holstein Cattle.** PMC11970297. **[verify]**
Casein proportions: αs1 ≈ 38% of total caseins, β ≈ 36%, κ ≈ 13%, αs2 ≈ 10%. κ-casein is 169 residues, ~13 kb gene, 14 variants. If the product is an artificial casein micelle, β-casein alone is insufficient — a calcium-insensitive κ-casein is required to cap growth.

**F5. UniProt accessions and phosphorylation-site distribution.**
P02662 (αs1), P02663 (αs2), P02666 (β-casein), P02668 (κ). Phosphate distribution: αs1 ≈ 8 phosphates concentrated centrally; αs2 ≈ 10–13; β-casein ≈ 5 phosphates concentrated at the N-terminus; κ typically 1–3 near the C-terminus, and uniquely can be phosphorylated on threonine as well as serine. The success criterion stated numerically: "fully phosphorylated β-casein" means 5P, N-terminally clustered.

## 8. Thread G — FAM20C biology

**G1. Tagliabracci VS, Engel JL, Wen J, Wiley SE, Worby CA, Kinch LN, Xiao J, Grishin NV, Dixon JE (2012).** Secreted kinase phosphorylates extracellular proteins that regulate biomineralization. *Science* 336:1150–1153.
The identification paper. Fam20C is the authentic Golgi casein kinase. It phosphorylated recombinant β-casein in a time-dependent manner while the catalytically inactive D478A mutant, unable to coordinate Mn²⁺, did not. Co-expression of V5-tagged αs1-casein with FLAG-tagged Fam20C in U2OS cells produced a mobility shift absent with D478A and reversed by λ-phosphatase. The substrate in the original demonstration was β-casein specifically.

**G2. Tagliabracci VS, et al. (2015).** A Single Kinase Generates the Majority of the Secreted Phosphoproteome. *Cell* 161:1619–1632. DOI 10.1016/j.cell.2015.04.028
Fam20C phosphorylates secreted proteins within S-x-E/pS motifs, including casein, FGF23, and the SIBLING family, and generates the majority of the extracellular phosphoproteome.

**G3. Cui J, Xiao J, Tagliabracci VS, Wen J, Rahdar M, Dixon JE (2015).** A secretory kinase complex regulates extracellular protein phosphorylation. *eLife* 4:e06120. DOI 10.7554/eLife.06120; PMC4421793
Fam20A is a pseudokinase acting as an allosteric activator of Fam20C. The Fam20C E306Q mutant showed greatly reduced in vitro kinase activity toward casein and abolished intrinsic ATPase activity. A design warning: co-expressing Fam20C alone may be insufficient.

**G4. Xiao J, Tagliabracci VS, Wen J, Kim SA, Dixon JE (2013).** Crystal structure of the Golgi casein kinase. *PNAS* 110:10574–10579.
The *C. elegans* ortholog structure: an atypical kinase-like fold with disulfide bridges, N-linked glycosylation, and a novel insertion domain conserved across Fam20 members. The disulfides and N-glycans mean the kinase itself must transit a secretory pathway to fold — why bacterial expression fails and why a Golgi-bearing host is credible.

**G5. Zhang H, et al. (2018).** Structure and evolution of the Fam20 kinases. *Nat Commun* 9:1218. Priority read for resolving D5.

**G6. Worby CA, Mayfield JE, Pollak AJ, Dixon JE, Banerjee S (2021).** The ABCs of the Atypical Fam20 Secretory Pathway Kinases. *J Biol Chem* 296:100267. PMC7948968

**G7. Chen X, Zhang J, Liu P, et al. (2021).** Proteolytic processing of secretory pathway kinase Fam20C by site-1 protease promotes biomineralization. *PNAS* 118(32):e2100133118
Fam20C resides in the Golgi as a transmembrane protein; site-1 protease cleaves the propeptide and promotes secretion and activation. A third design fork: if S1P processing is required, a pre-cleaved or propeptide-free FAM20C construct may be necessary.

**G8. Ancestral roles of the Fam20C family of secreted protein kinases revealed in *C. elegans* (2019).** *J Cell Biol* 218(11):3795. **[verify]**

**G9. Comprehensive Analysis of the Putative Substratome of FAM20C, the Master Serine Kinase of the Secretory Pathway.** PMC12650399 (~2025). **[verify]**
CK1 and CK2 were named for casein but lack the correct localization and do not recognize the SxE motifs; a Golgi casein kinase activity was detected in lactating mammary gland in 1972; a synthetic peptide corresponding to a bovine β-casein phosphorylation site, β(28–40), was selectively phosphorylated by GCK but not CK1 or CK2; by 2010, 50–70% of secreted phosphosites in plasma and CSF matched the S/TxE consensus. β(28–40) is a ready-made assay substrate for validating any FAM20C construct.

## 9. Thread H — Phosphorylation in heterologous hosts (prior-art benchmark)

**H1. Mora Vásquez S, García-Jacobo S, Cardineau GA, García-Lara S (2025).** Heterologous Caseins: The Role of Phosphorylation in Their Functionality and How to Achieve It. *Biomolecules* 15(7):1031. DOI 10.3390/biom15071031; PMC12292773
The keystone review. Systematic search of literature and patent databases for heterologous casein expression. Table 1 — 17 bacterial studies. Table 2 — 5 yeast studies, expression 0.6 mg/L to 1 g/L. Table 3 — 2 plant studies (potato 0.01%; soybean 0.1–0.4%, not phosphorylated). Table 4 — 12 patents, 2022–2024. Reviews four phosphorylation analysis methods (MALDI-MS / LC-ESI-MS; SDS-PAGE with Ethyl Stains-All; Urea-PAGE with phosphatase treatment; Phos-tag), and three enhancement strategies. Concludes that quantitative functional thresholds — how much calcium-binding is lost, what minimum phosphorylation supports curd formation — remain unestablished. Records "undetermined" for most bacterial studies because the analysis was never done.

**H2. Thurmond JM, et al. (1997).** Expression and Characterization of Phosphorylated Recombinant Human Beta-Casein in *Escherichia coli*. *Protein Expr Purif* 10:202–208.
Polycistronic construct encoding human β-casein with both α and β subunits of human CK2. Achieved high-level phosphorylated recombinant human β-casein at 500 mg/L, characterized by urea-PAGE, SDS-PAGE and negative-ion LC-ESI-MS. The highest-yield phosphorylated recombinant casein on record.

**H3. Clegg RA, Holt C (2009).** An *E. coli* over-expression system for multiply-phosphorylated proteins and its use in a study of calcium phosphate sequestration by novel recombinant phosphopeptides. *Protein Expr Purif* 67:23–34.
The companion negative result. Bovine β-casein co-expressed with CK2 achieved much lower phosphorylation than the native 5P state. In human β-casein the serine clusters align well with CK2 consensus sites; in bovine β-casein only some cluster serines sit in canonical CK2 sites. Yield 200 mg/L, partially phosphorylated (infusion MS of purified phosphopeptides). H2 and H3 together are the decisive argument for FAM20C over CK2 in a bovine program.

**H4. Choi BK, Jiménez-Flores R (2001).** Expression and Purification of Glycosylated Bovine β-Casein (L70S/P71S) in *Pichia pastoris*. *J Agric Food Chem* 49:1761–1766. DOI 10.1021/jf001298f
The closest eukaryotic precedent. L70S/P71S mutations introduced an N-glycosylation site. Despite using the native bovine β-casein signal peptide for secretion, the protein localized mostly intracellularly at approximately 15–18% of total soluble protein, corresponding to 0.7–1.0 g/L; secreted protein reached only 0.005% of the intracellular level. Phosphorylation analysis (phosphatase treatment + Urea-PAGE) showed the recombinant protein carried the same degree of phosphorylation as animal-derived β-casein. The protein was N-glycosylated with mannan. The single most instructive paper for the cw15 program.

**H5. Choi BK, Jiménez-Flores R (1996).** Study of putative glycosylation sites in bovine β-casein introduced by PCR-based site-directed mutagenesis. *J Agric Food Chem* 44:358–364. Reported at 1 g/L.

**H6. Jimenez-Flores R, Richardson T, Bisson LF (1990).** Expression of bovine β-casein in *Saccharomyces cerevisiae*. *J Agric Food Chem* 38:1134–1141. Yeast-produced and bovine casein showed the same urea-gel mobilities before and after dephosphorylation. Protein was retained in the periplasmic space.

**H7. Chung KS, Oh SS, Richardson T (1991).** Secretion of bovine β-casein by *Saccharomyces cerevisiae*. *J Microbiol Biotechnol* 1:31–36. 10 mg/L; only 5–10% of total expressed casein reached the extracellular medium.

**H8. Balasubramanian S, Mobasseri G, Shi L, Jers C, Køhler JB, Boire A, Berton-Carabin C, Mijakovic I, Jensen PR (2025).** Production of phosphorylated and functional αs1-casein in *Escherichia coli*. *Trends Biotechnol*. DOI S0167779925001817
Five kinases screened for S-x-E/pS specificity: three prokaryotic Hanks-type Ser/Thr kinases from *Bacillus subtilis* (PrkC, PrkD, YabT) and eukaryotic FAM20C from human and bovine. Attempts to express both FAM20C versions in *E. coli* failed — successful human FAM20C expression has to date been achieved only in human cell lines. A phosphomimetic route was built in parallel: all eight phosphoserine sites of αs1-casein variant B substituted with aspartate. The strongest single argument for a eukaryotic host with a secretory pathway.

**H9. Balasubramanian S (2025).** Precision fermentation of milk proteins. PhD thesis, DTU. Six chapters covering *C. glutamicum* genetic element optimization, phosphorylated and phosphomimetic proteins in *E. coli*, recombinant caseins in plant–animal protein hybrids, and whey proteins from alfalfa. Includes a patent: Method to produce phosphorylated milk proteins in microbe (Jers, Shi, et al., 2023).

**H10. Navone L, Moffitt K, Behrendorff J, Sadowski P, Hartley C, Speight R (2023).** Biosensor-guided rapid screening for improved recombinant protein secretion in *Pichia pastoris*. *Microb Cell Fact* 22:92. DOI 10.1186/s12934-023-02089-z
Split-GFP biosensor with a GFP1-10–TEV protease fusion in the ER; GFP11-tagged cargo complements on transit, so intracellular fluorescence tracks secretion. Validated on four cargoes including β-casein and β-lactoglobulin, with β-casein monitored under methanol induction at 72–130 h. A directly transplantable screening protocol.

**H11. Simons G, van den Heuvel W, Reynen T, Frijters A, Rutten G, Slangen CJ, Groenen M, de Vos WM, Siezen RJ (1993).** Overproduction of bovine β-casein in *E. coli* and engineering of its main chymosin cleavage site. *Protein Eng* 6:763–770.

**H12. Hansson L, Bergström S, Hernell O, Lönnerdal B, Nilsson AK, Strömqvist M (1993).** Expression of human milk β-casein in *E. coli*. *Protein Expr Purif* 4:373–381. Not phosphorylated.

**H13. Bu H, Hu Y, Sood SM, Slattery CW (2003).** Comparison of native and recombinant non-phosphorylated human β-casein. *Arch Biochem Biophys* 415:213–220.

**H14. Wang Y, Kubiczek D, Horlamus F, Raber HF, Hennecke T, Einfalt D, Henkel M, Hausmann R, Wittgens A, Rosenau F (2021).** Bioconversion of lignocellulosic 'waste' to high-value food proteins: recombinant production of bovine and human αs1-casein based on wheat straw lignocellulose. *GCB Bioenergy* 13:640–655. 1.45 g/L — the highest bacterial casein titer in the corpus.

**H15. Philip R, et al. (2001).** Bovine β-casein in soybean (*Glycine max*), 0.1–0.4% of total soluble protein, not phosphorylated by MALDI-MS. Enrichment used anti-casein antibody coupled to CNBr-activated Sepharose 4B. Also: human β-casein in *Solanum tuberosum*, 0.01%; migrated as a single ~30 kDa band, 1–1.5 kDa smaller than the phosphorylated control.

**H16. Shigemori S, et al. (2012).** Expression of a biologically active GFP-αs1-casein fusion in *Lactococcus lactis*. *Curr Microbiol* 64:569–575. A food-grade host precedent.

**H17. The patent landscape (H1 Table 4).**
US12139737B2 (Nobell Foods) — host cells comprising a recombinant casein protein and a recombinant kinase protein; explicitly incorporates Fam20C. The closest prior art to the cw15 strategy. WO2023092005A1 and WO2023197002A2 (Mozza Foods) — phosphorylation of proteins in plants. WO2024013749A1 (Imagene Foods) — functional milk proteins in plant cells co-expressed with at least one kinase. US12077798B2 (Nobell Foods) — transgenic plants stably expressing recombinant fusion milk proteins at ≥1% of total soluble protein. WO2024015365A1 (Kiverdi) — recombinant food proteins in chemoautotrophic microorganisms, host list includes algae; the only algal claim found. US12359212 — recombinant micelle and in vivo assembly; co-infiltration of *N. benthamiana* with bovine κ-casein (pMOZ700) and BtFam20C (pMOZ14) constructs.

## 10. Thread I — Functionality: does phosphorylation matter?

**I1. Che J, Fan Z, Bijl E, Thomsen JPS, Mijakovic I, Hettinga K, Poulsen NA, Larsen LB (2025).** Unravelling the dominant role of phosphorylation degree in governing the functionality of reassembled casein micelles. *Food Hydrocolloids* 159:110615. DOI 10.1016/j.foodhyd.2024.110615
Four caseins purified from bovine milk and enzymatically dephosphorylated to three pools, then reassembled into nine micelle solutions across three systems. Micelle reassembly ability was proportional to phosphorylation degree; higher phosphorylation gave a higher micellar proportion and greater calcium-binding; fully dephosphorylated caseins hardly formed micelle structures at all and remained in serum. Gelation pH rose as phosphorylation fell, and fully dephosphorylated caseins failed to gel entirely, precipitating at their isoelectric point around pH 5.5. Across all three systems roughly 87% of total protein was sedimentable in the fully phosphorylated case. The success criterion, experimentally grounded: if a cw15-derived β-casein cannot be phosphorylated, it will not gel — it will precipitate.

**I2. Antuma LJ, Steiner I, Garamus VM, Boom RM, Keppler JK (2023).** Engineering artificial casein micelles for future food: Is casein phosphorylation necessary? *Food Res Int* 173:113315. DOI 10.1016/j.foodres.2023.113315
Artificial casein micelles composed predominantly of dephosphorylated casein form irregular structures roughly three times larger than normal.

**I3. Antuma LJ, Braitmaier SH, Garamus VM, Hinrichs J, Boom RM, Keppler JK (2024).** Engineering artificial casein micelles for future food: Preparation rate and coagulation properties. *J Food Eng* 366:111868. Micellar diameter is controllable by preparation rate during assembly.

**I4. Antuma LJ, Stadler M, Garamus VM, Boom RM, Keppler JK (2024).** Casein micelle formation as a calcium phosphate phase separation process. *Innov Food Sci Emerg Technol* 92:103582. Replaces the unscalable dropwise-mixing method with vacuum evaporation and membrane routes — the unit operation that would sit downstream of a cw15 fermentation.

**I5. Antuma LJ (2025).** Artificial casein micelles and the road towards animal-free cheese. PhD thesis, Wageningen University, 239 pp.

**I6. Raynes JK, Mata J, Wilde KL, Carver JA, Kelly SM, Holt C (2024).** Structure of biomimetic casein micelles: critical tests of the hydrophobic colloid and multivalent-binding models using recombinant deuterated and phosphorylated β-casein. *J Struct Biol X* 9:100096. PMC10840362 The most structurally rigorous validation target for a cw15-derived product.

**I7. Chezan D, Fuhrmann PL, Bender D, Rennhofer H, Domig KJ, Dewi BPC (2026).** Physicochemical properties of native and precision fermentation-derived bovine β-casein. *Food Hydrocolloids* 171:111797. DOI 10.1016/j.foodhyd.2025.111797 The head-to-head comparison. Priority ingest.

**I8. Koudelka T, Hoffmann P, Carver JA (2009).** Dephosphorylation of αs- and β-caseins and its effect on chaperone activity. *J Agric Food Chem* 57:5956–5964. Phosphoserine-driven structural flexibility underpins casein's molecular-chaperone behavior — lost, not merely reduced, on dephosphorylation.

**I9. Counterweight — when phosphorylation may not be required. [verify]**
Mortes et al. (2026) report that recombinant non-phosphorylated αs1-casein can stabilize emulsion and foam interfaces, indicating that for some food applications phosphorylation may be unnecessary. *Tuning the structure and coagulation behaviour of artificial casein micelles by varying the casein composition* (*Food Hydrocolloids*, 2025) shows functional artificial micelles can be built from two or three caseins rather than all four. *Artificial and reformed casein micelles as encapsulation vehicles* (*Crit Rev Food Sci Nutr*, 2025, DOI 10.1080/10408398.2025.2513522) notes ACM formation from recombinant caseins has so far been unsuccessful, largely for PTM reasons. The product-strategy fork: emulsifier/foaming applications are reachable without solving FAM20C; cheese and yogurt are not.

## 11. Thread J — Purification and downstream processing

**J1. Keppler JK, Boom RM (2026).** Downstream Processing of Food Proteins from Precision Fermentation. *Annu Rev Food Sci Technol*. DOI 10.1146/annurev-food-060424-091647
Conventional chromatography is designed for high-purity, high-value products and is too costly for bulk food proteins; cost-effective production requires prioritizing ingredient functionality — emulsifying, foaming, gelation — over purity. Discusses coacervation with food-grade polyanions, and notes the calcium sensitivity of α- and β-caseins can itself enable simplified extraction.

**J2. Atamer Z, et al. (2017).** See E1. Doubles as the isolation-technology review: selective precipitation exploiting calcium sensitivity by adding calcium chloride at alkaline pH, and cold membrane filtration at ≤4 °C exploiting β-casein dissociation from the micelle into the serum phase.

**J3. Schäfer J, Schubert T, Atamer Z (2019).** Pilot-scale β-casein depletion from micellar casein via cold microfiltration in the diafiltration mode. *Int Dairy J* 97:222–229.

**J4. Schubert T, Ergin I, Panetta F, Hinrichs J, Atamer Z (2021).** Application of a temperature-controlled decanter centrifuge for the fractionation of αS-, β- and κ-casein at pilot scale. *Int Dairy J* 122:105148.

**J5. Post AE, Ebert M, Hinrichs J (2009).** β-casein as a bioactive precursor — processing for purification. *Aust J Dairy Technol* 64:84–88.

**J6. Post AE, Hinrichs J (2011).** Large-scale isolation of food-grade β-casein. *Milchwissenschaft* 66:361–364.

**J7. Post A, Arnold B, Weiss J, Hinrichs J (2012).** Effect of temperature and pH on the solubility of caseins. *J Dairy Sci* 95:1603–1616. Solubility surfaces in temperature × pH — directly usable for isoelectric precipitation of recombinant β-casein at pI 4.6.

**J8. van der Schaaf JM, Goulding DA, Fuerer C, O'Regan J, O'Mahony JA, Kelly AL (2024).** A novel approach to isolation of β-casein from micellar casein concentrate by cold microfiltration combined with chymosin treatment. *Int Dairy J* 148:105796.

**J9. Mannan interference and purification efficiency in downstream processing of precision-fermented milk proteins from *Komagataella phaffii*. [verify]** Yeast mannan is the analogue of the UVM4 cell-wall-glycoprotein aggregate problem.

**J10. Postma PR, et al. (2017).** Mild and Selective Protein Release of Cell Wall Deficient Microalgae with Pulsed Electric Field. *ACS Sustain Chem Eng*. DOI 10.1021/acssuschemeng.7b00892
PEF applied to a cell-wall-deficient mutant gave an average protein yield of 31 ± 6% versus 11 ± 3% for the walled wild type (p < 0.05) — roughly three-fold, comparable to mechanical disruption but under mild conditions. The record that converts "cw15 is easy to transform" into "cw15 is cheap to process."

**J11. Mechanical disruption benchmarks for microalgae. [verify]**
Safi C, et al. — *Energy consumption and water-soluble protein release by cell wall disruption of Nannochloropsis gaditana*: high-pressure homogenization and bead milling were most efficient, giving >95% cell disintegration, approximately 50% (w/w) release of total proteins, at low energy input (<0.5 kWh per kg biomass). *Microalgae Cell Disruption Methods* (Encyclopedia MDPI, 2021) records PEF released a maximum of 13% of protein from walled *Chlorella vulgaris* even at 10–100× the energy of bead milling, which released 45–50%. J10 and J11 read together: PEF on walled cells is bad; PEF on wall-deficient cells is competitive with bead milling at mild conditions.

## 12. Thread K — Comparable successes in other hosts

**K1. Aro N, Ercili-Cura D, Andberg M, Silventoinen P, Lille M, Hosia W, Nordlund E, Landowski CP (2023).** Production of bovine beta-lactoglobulin and hen egg ovalbumin by *Trichoderma reesei* using precision fermentation technology. *Food Res Int* 163:112131. DOI 10.1016/j.foodres.2022.112131
1 g/L β-lactoglobulin and 2 g/L ovalbumin, at both 24-well plate and bioreactor scale. Circular dichroism confirmed the recombinant β-Lg matched native bovine secondary structure and showed comparable emulsification. The recombinant proteins were N-glycosylated with mannose-containing five-sugar-unit glycans typical of fungal hosts. The benchmark every openFerment scenario is measured against — 1 g/L secreted from a fungus vs 15 mg/L from UVM4 is a 65× gap.

**K2. Omics-guided global rewiring of yeast metabolism enables high-level production of β-lactoglobulin (2026). [verify]**
Methanol-free *K. phaffii* β-Lg platform; transcriptomic and metabolomic identification of bottlenecks across energy supply, TCA-linked carbon and nitrogen metabolism, amino acid metabolism, redox homeostasis, and protein folding/secretion. Cites LCA figures for precision-fermented vs conventional dairy delivery of equivalent β-Lg: approximately 70% lower greenhouse-gas impact, around 80% less water use, and nearly 99% less arable land (Kossmann et al., 2025).

**K3. Batt CA, et al. (1990).** Expression of recombinant bovine β-lactoglobulin in *Escherichia coli*. *Agric Biol Chem* 54:949. Accumulated predominantly as insoluble inclusion bodies.

**K4. Kim et al. (1997).** Secretory β-lactoglobulin production in *P. pastoris*; the basis on which several companies now commercialize recombinant β-Lg.

**K5. Animal-free caseins by precision fermentation: technical challenges and perspectives (2026).** *Trends Food Sci Technol* PII S092422442600350X. **[verify]**
The most current review of the exact problem. Secretion is highly advantageous for caseins because it avoids cell disruption and extensive purification; documents the yeast secretion failures; reiterates that phosphorylation is critical for micelle formation and for both acid and rennet coagulation; notes that when expressed in yeast, recombinant caseins can acquire O-glycosylation absent from the animal-derived protein. Publisher blocks automated retrieval. VERIFY AT INGEST whether this review already names microalgae as a candidate host — if so, §0's white-space claim must be revised.

**K6. Hettinga K, Bijl E (2022).** Can recombinant milk proteins replace those produced by animals? *Curr Opin Biotechnol* 75:102690.

**K7. Deng M, Lv X, Liu L, Li J, Du G, Chen J, Liu Y (2023).** Cell factory-based milk protein biomanufacturing: advances and perspectives. *Int J Biol Macromol* 244:125335.

**K8. Dupuis JH, Cheung LKY, Newman L, Dee DR, Yada RY (2023).** Precision cellular agriculture: the future role of recombinantly expressed protein as food. *Compr Rev Food Sci Food Saf* 22(2):882–912.

**K9. Piazenski IN, et al. (2024).** From lab to table: the path of recombinant milk proteins in transforming dairy production. *Trends Food Sci Technol* 149:104562.

**K10. Food production from air: gas precision fermentation with hydrogen-oxidising bacteria (2025).** *Trends Biotechnol* PII S0167-7799(25)00321-X. **[verify]**
Milk protein titers from microbial fermentation have risen roughly a thousandfold over thirty years, from about 0.001 g/L in 1990 to about 1 g/L, against roughly 3 g/L β-lactoglobulin in bovine milk. Reported yields of at least 6 g/L for heterologous secretion via engineered *E. coli* secretion systems; the highest β-Lg levels have been achieved in *T. reesei*.

## 13. Thread L — Products: the plant-based gap that casein fills

**L1. Grossmann L, McClements DJ (2021).** *Trends Food Sci Technol* — the canonical statement of plant-based cheese sensory shortfalls. **[verify]**

**L2. Overcoming the flavour and textural/rheological problems of plant-based cheese alternatives (2024).** *Food Chem Adv* PII S266683352400234X. **[verify]**
Documents the starch-based structuring paradigm and its limits: increasing starch causes excessive hardening and reduced meltability; native starch prevents melting while oxidized starch improves it; pregelatinized starch as a casein and fat replacer improves softness, cohesiveness, and meltability; zein-containing analogues melt like cheese while pea-protein-isolate products do not, with a zein/PPI blend at 30% total protein showing melting potential.

**L3. Investigation of various plant protein ingredients for processed cheese analogues (2025).** *Int J Food Sci Technol* 60(1):vvae018.
Cheddar showed the highest hardness, firmness and Young's modulus (126.8 N, 98.81 N, 953.3 kPa); plant-based products displayed poor meltability attributed to the absence of a continuous protein network. Zein has melt-stretch and viscoelastic properties resembling Cheddar but suffers poor solubility, limited nutritional value, flavor issues, and processing difficulty.

**L4. Plant-based cheese analogs: structure, texture, and functionality (2025). [verify]** In the absence of casein, plant-based cheeses develop brittle or gummy textures, and plant protein/fat instability causes phase separation and poor structural cohesion.

**L5. Sensory evaluation of plant-based cheese: a systematic review with a focus on texture and mouthfeel (2025).** *Crit Rev Food Sci Nutr*. DOI 10.1080/10408398.2025.2531220

**L6. Cheese Analogues, an Alternative to Dietary Restrictions and Choices.** PMC12294849. **[verify]** PRISMA review; 1,553 articles and 155 patents screened, 88 articles and 66 patents analyzed; interest rising since 2020 and peaking in 2024.

**L7. Andrigo et al. (2025).** Development of a Novel Robust Approach for Unveiling the Stretchiness of Cheese. *J Texture Stud*. DOI 10.1111/jtxs.70012 Stretchiness is among the hardest attributes to imitate and lacks standardized measurement, with the fork test still dominant.

**L8. Towards meltable plant-based cheese alternatives: processing oil and fat in zein-pea hybrids (2026).** PII S2772502226003185. **[verify]** Commercially available alternatives contain little protein and are high in carbohydrates; coconut fat or sunflower oil produce waxy or oily textures.

## 14. Thread M — Cultivation: cw15 growth and TAP medium

**M1. Harris EH (1989).** *The Chlamydomonas Sourcebook*. Academic Press. TAP medium reference. Standard cultivation: liquid or agar-solidified TAP at 22 °C under continuous light at 50–100 µE m⁻² s⁻¹, mixotrophic.

**M2. Gorman DS, Levine RP (1965).** *PNAS* 54:1665–1669. The original Tris-acetate-phosphate formulation. **[verify]**

**M3. Kropat J, Hong-Hermesdorf A, Casero D, Ent P, Castruita M, Pellegrini M, Merchant SS, Malasarn D (2011).** A revised mineral nutrient supplement increases biomass and growth rate in *Chlamydomonas reinhardtii*. *Plant J* 66:770–780. **[verify]** The modern trace-element recipe.

**M4. Metabolic rewiring and biomass redistribution enable optimized mixotrophic growth in *Chlamydomonas* (2026).** *PNAS*. DOI 10.1073/pnas.2522572123. **[verify]**
¹³C flux analysis: mixotrophic cultures grow far faster than either phototrophic or heterotrophic cultures even though acetate partially suppresses photosynthesis. Acetate induced the glyoxylate cycle and suppressed gluconeogenesis while reducing photosynthetic flux; partial photosynthesis suppression may itself optimize growth by reducing the protein-synthesis burden — directly relevant to a host asked to overexpress two heterologous proteins.

**M5. A Carbon Fixation Enhanced *Chlamydomonas reinhardtii* Strain for Achieving the Double-Win Between Growth and Biofuel Production (2020).** *Front Bioeng Biotechnol* 8:603513. **[verify]**
Wild-type CC-137c in TAP reached a maximum density of 1.23 ± 0.13 g/L within 96 h with maximum biomass productivity 24.30 ± 1.65 mg L⁻¹ h⁻¹; a cGAPDH-overexpressing strain reached 1.74 ± 0.09 g/L and 28.54 ± 1.43 mg L⁻¹ h⁻¹.

**M6. Moon M, et al. (2013).** Mixotrophic growth with acetate or volatile fatty acids maximizes growth and lipid production in *Chlamydomonas reinhardtii*. *Algal Res*. **[verify]** Greatest biomass production 2.15 g L⁻¹ in 5 days with FAME yield 16.41% of biomass, under mixotrophic cultivation with acetate.

**M7. Effect of the Light Regime and Phototrophic Conditions on Growth of *C. reinhardtii* (Energy Procedia, 2012). [verify]**
Strain cc124 in TAP showed its fastest growth rate, r = 0.087 h⁻¹, with 0% CO₂ feed — acetate is used far more effectively than CO₂, and adding CO₂ to acetate-replete TAP only reduces growth rate. Maximum final density was calculated at a CO₂ feed of 7.9%. The corpus's cleanest specific-growth-rate record.

**M8. Density and nutrient optimization. [verify]**
*Reducing culture medium nitrogen supply coupled with replenishing carbon nutrient* (PMC9549070): response-surface optimum at 4.12 g/L sodium acetate and 0.20 g/L NH₄Cl, giving 32.14% total lipid, 1.68 g/L biomass, and 108.21 mg L⁻¹ d⁻¹ lipid productivity; standard TAP contains 0.38 g/L NH₄Cl. **Chen F, Johns MR (1996)**, *Process Biochem* — heterotrophic growth on acetate in chemostat, highest cell concentration 1.5 g/L at 3.4 g/L feed acetate. Heterotrophic microalgal cultures can reach 50–100 g/L dry biomass versus a maximum around 30 g/L autotrophically. The density gap between 1–2 g/L mixotrophic *Chlamydomonas* and 100+ g/L *Pichia* fed-batch is the harshest number in the corpus for the cw15 thesis.

## 15. Thread N — Food safety and regulatory position

**N1. Fields FJ, Lejzerowicz F, Schroeder D, Ngoi SM, Tran M, McDonald D, Jiang L, Chang JT, Knight R, Mayfield S (2020).** *J Funct Foods*. **[verify]** *C. reinhardtii* GRAS status and human gastrointestinal-health study.

**N2. Microalgae as a future food source.** OSTI 1822262. **[verify]**
Records the short list of microalgae with FDA GRAS status: *Arthrospira platensis*, *Chlamydomonas reinhardtii*, *Auxenochlorella protothecoides*, *Chlorella vulgaris*, *Dunaliella bardawil*, *Euglena gracilis*. GRAS applies only in U.S. jurisdiction.

**N3. EFSA NDA Panel (2025).** Safety of dried biomass powder of *Chlamydomonas reinhardtii* THN 6 as a novel food pursuant to Regulation (EU) 2015/2283. *EFSA J* 23:e9413. DOI 10.2903/j.efsa.2025.9413; PMC12041885
Triton Algae Innovations applied in April 2023. EFSA identified data gaps across identity, production process, composition, specifications, history of use, proposed uses and use levels, nutritional information, genotoxicity and allergenicity, requested additional information repeatedly, received no reply, and concluded that the safety of the novel food could not be established. The corpus's most important cautionary record: U.S. GRAS status does not transfer to the EU, an actual *C. reinhardtii* food application has failed on the record, and the failure was procedural rather than a finding of harm.

**N4. Towards microalga-based superfoods: heterologous expression of zeolin in *Chlamydomonas reinhardtii* (2023).** *Front Plant Sci*. PMC10203602. **[verify]**
A synthetic gene encoding zeolin, a chimera of γ-zein and phaseolin, introduced into the algal genome. The closest published precedent to the entire program — a heterologous food protein expressed in *C. reinhardtii* for nutritional purposes. Priority ingest.

## 16. Thread O — Techno-economic analysis and process modeling

**O1. Cortes-Peña Y, Kumar D, Singh V, Guest JS (2020).** BioSTEAM: A Fast and Flexible Platform for the Design, Simulation, and Techno-Economic Analysis of Biorefineries under Uncertainty. *ACS Sustain Chem Eng* 8(8):3302–3310. DOI 10.1021/acssuschemeng.9b07040
Open-source steady-state process simulator in Python; economic metrics closely match SuperPro Designer and Aspen Plus; evaluated 31,000 biorefinery designs in under 50 minutes. The platform's simulation engine — and Deepak Kumar is a co-author.

**O2. Good Food Institute (2025).** Techno-economic insights on fermentation ingredients.
Meta-analysis of 55 published techno-economic models. Biomass-fermentation protein costs converge around $4–6/kg, against beef and pork market prices of $6.0–15.0/kg. Microbial oils range $1.5–19.6/kg. Published models assume production volumes of 50–2,500 t/y and average titer around 24 g/L, while private-sector benchmarks span 2,500–25,000 t/y and average around 42 g/L — a gap wide enough that published models systematically overstate cost. Reported estimates span under $20/kg to about $15,000/kg with a conspicuous absence of models in the $20–200/kg band. The single richest TEA source in the corpus.

**O3. Techno-economic analysis of industrial-scale fermentation for formate dehydrogenase production (2025).** PMC12681506. **[verify]**
Four scenarios all sized to deliver 80,000 kg pure protein per year. Minimum selling price for crude protein ranged $2,300/kg (1 L empirical) to $75/kg (optimistic); purified protein ranged $99,000/kg to $970/kg. A clear inverse relationship held between levelized protein cost and two upstream parameters: biomass cell density and target protein content — the 1 L case ran at 4.2 g/L biomass with target protein at 0.1% of cell mass. The most directly transferable cost model in the corpus.

**O4. Acién FG, Fernández JM, Magán JJ, Molina E (2012).** Production cost of a real microalgae production plant and strategies to reduce it. *Biotechnol Adv*. PMID 22361647
Ten 3 m³ tubular photobioreactors, continuous mode, two years of data on *Scenedesmus almeriensis* in Almería. Annual capacity 3.8 t/y (90 t/ha·y), photosynthetic efficiency 3.6%, production cost 69 €/kg, dominated by labor and depreciation. Simplification plus scale-up to 200 t/y reduces cost to 12.6 €/kg.

**O5. Towards microalgal triglycerides in the commodity markets.** *Biotechnol Biofuels* (2017). PMC5514516. **[verify]**
100-ha plant in southern Spain, vertically stacked tubular PBRs: 6.7 €/kg biomass at 24% TAG. Photosynthetic efficiency is the single most influential parameter (30% and 14% cost reduction from base case for stress and growth phases); avoiding active cooling gives 10%, raising the cooling setpoint 4.5%. All improvements together project 3.3 €/kg at 60% TAG. A ready-made tornado chart from real data.

**O6. Schade S, Meier T (2021).** Techno-economic assessment of microalgae cultivation in a tubular photobioreactor for food in a humid continental climate. *Clean Technol Environ Policy*. DOI 10.1007/s10098-021-02042-x Borosilicate glass tubing is one of the largest single capital items; residual protein-rich biomass co-product was valued at only 0.44 EUR/kg DM.

**O7. Techno-economic assessment of microalgae production, harvesting and drying (2022).** PMID 35526636. **[verify]**
*Nannochloropsis oceanica* year-round cultivation: 53.32 €/kg DW at 27.61 t/y for 1 ha. Centrifugation contributed 10.65% of biomass cost and freeze-drying 20.15%; substituting ultrafiltration plus spray drying cut costs 7.03%, expanding to 10 ha cut 17.99%, and using fertilizers instead of commercial nutrient solutions cut 10.92%.

**O8. Precision fermentation cost trajectory — a deliberately mixed-quality cluster.**
Peer-reviewed anchor: **Knychala MM, Boing LA, Ienczak JL, Trichez D, Stambuk BU (2024)**, Precision Fermentation as an Alternative to Animal Protein, *Fermentation* 10(6):315, DOI 10.3390/fermentation10060315 — cost falling from about USD 1 million/kg in 2000 to roughly USD 100/kg currently, forecast below USD 10/kg by 2030.
NON-PEER-REVIEWED market and vendor sources report precision-fermentation whey protein at $25–30/kg in 2025 targeting $8–12/kg by 2028, casein parity around 2028–2030, media at 35–50% of COGS, fermenters of 100,000–200,000 L needed for sub-$25/kg, and single-facility CAPEX of $150–400M. HANDLING RULE: ingest these but assign provenance class `industry-estimate`, render with a distinct tick, and never allow them into the gold set or default aggregate statistics.

## 19. Traps in this corpus (curation notes)

**Precursor versus mature numbering.** β-casein is 224 residues as translated and 209 after signal-peptide removal. Phospho-site positions, the A1/A2 codon-67 SNP, and the β(28–40) assay peptide are all quoted in mature numbering. Any record carrying a residue position must also carry the numbering convention.

**"Casein kinase" is three different enzymes.** CK1, CK2, and FAM20C. CK1 and CK2 were misnamed in 1969 and do not recognize the S-x-E motifs. `kinase_identity` must be an enum.

**"Cell wall deficient" spans several distinct genotypes.** cw15, cw15-302, CC-4350, cwd mt+ arg7, Elow47, UVM4, UVM11 are related but not interchangeable. Build an explicit strain-alias table before ingest.

**Expression units are heterogeneous by design.** % of total soluble protein, % of total cell protein, mg/L, g/L all appear. They are not comparable — hence ontology Rule 2.

**Citation-of-a-citation.** 15 mg/L appears as both the Ramos-Martinez (C2) measurement and, separately, in the UVM4 secretome paper's (C6) summary of prior work. The second is a citation, not an independent measurement. Strip plots overstate consensus unless records carry an `is_primary` flag.

**Publisher access.** ScienceDirect blocks automated retrieval. Roughly 55% of this corpus is openly retrievable. Plan ingestion in two passes.
