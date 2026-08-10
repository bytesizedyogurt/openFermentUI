// Corpus set B — SP-006 … SP-011, records ex-0043 … ex-0090.
// All content is synthetic: fictional authors, invented venues, no real DOIs.
// Section text is authored first; every record.quote is copied verbatim from it
// (BUILD-SPEC invariant 1). record.si is recomputed in src/data/records.ts.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_B: Paper[] = [
  {
    id: 'SP-006',
    title:
      'Comparative disruption of Chlamydomonas reinhardtii cw15 by bead milling and high-pressure homogenisation on a common pilot-scale feed',
    authors: [
      'Ingrid Vasstrand',
      'Kwabena Osei-Bonsu',
      'Rina Takamura',
      'Diogo Perotti Alencar',
      'Marta Lengyel',
    ],
    year: 2021,
    venue: 'Journal of Applied Phycotechnology',
    organisms: ['cw15'],
    topics: ['cell disruption', 'bead milling', 'high-pressure homogenization', 'downstream processing'],
    abstract:
      'Disruption is the largest single contributor to downstream energy demand in microalgal processes, yet published disruption efficiencies for Chlamydomonas reinhardtii are difficult to compare because feed concentration, temperature and the assay used to score lysis all vary between studies. We held those three variables fixed and compared bead milling with two-stage high-pressure homogenisation on a single pilot-scale feed of the cell-wall-deficient strain cw15, harvested by continuous disc-stack centrifugation. Lysis was scored by flow cytometry against an undisrupted control from the same feed, and soluble protein release was measured in parallel by the Lowry method. A single bead-mill pass outperformed a single homogeniser pass by more than five percentage points at lower specific energy, while three homogeniser passes closed the gap at a 2.4-fold energy penalty. Protein release and cell counts diverged for the homogeniser, indicating that permeabilised cells are scored as disrupted before their internal compartments release protein. We also report the harvest recovery of the step that produced the feed, because harvest and disruption yields multiply into the same overall recovery and are too often reported in isolation.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Chlamydomonas reinhardtii is attractive as a chassis for recombinant protein and pigment production, but almost every product of interest is intracellular. Disruption therefore sits on the critical path of any process built around this organism, and at pilot scale it is usually the single largest contributor to downstream energy demand. The cw15 lineage is routinely described as cell-wall-deficient, which invites the assumption that it lyses readily. In practice cw15 retains a substantial glycoprotein layer and an intact plasma membrane, and the disruption efficiencies reported for this strain span a range wide enough that they cannot all be describing the same physical event.\n\n' +
          'Two mechanical routes dominate at production scale. Bead milling delivers energy through a stirred bed of small grinding media and is comparatively insensitive to feed viscosity, which matters when the feed is a centrifuge paste rather than a dilute culture. High-pressure homogenisation forces the suspension through a narrow valve gap and relies on cavitation and shear at the valve seat; it is easier to clean and to validate, but its efficiency falls sharply for small, deformable cells that deform rather than fracture. Neither route is obviously superior for a wall-deficient green alga, and the available comparisons rarely hold feed concentration, temperature and the disruption assay constant across the two operations.\n\n' +
          'A second and less discussed source of disagreement is the assay itself. Loss of countable intact cells, release of soluble protein, release of a specific marker enzyme and turbidity decay all report different fractions of the same population, and the ordering between them depends on the mechanism of disruption. A method that permeabilises the plasma membrane without fragmenting the cell will score highly by dye exclusion and poorly by protein release.\n\n' +
          'We therefore compared the two unit operations on a common feed, holding biomass concentration, jacket temperature and analytical method fixed, so that the resulting efficiencies are directly comparable. A bath sonication reference was included, not as a candidate unit operation, but as the laboratory method against which many small-scale claims are still made.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Chlamydomonas reinhardtii cw15 was grown mixotrophically in Tris-acetate-phosphate medium in a 120 L stirred photobioreactor under continuous illumination. Cultures were harvested at a dry cell weight of 2.6 g L⁻¹, 96 h after inoculation, when residual acetate in the broth had fallen below 0.2 g L⁻¹. Dry cell weight was determined in triplicate by filtering 20 mL of culture onto pre-weighed glass-fibre filters, washing twice with ammonium formate to remove medium salts, and drying to constant mass.\n\n' +
          'Harvest was by continuous disc-stack centrifugation at a feed rate of 90 L h⁻¹ and a bowl speed equivalent to 8,500 × g. Gravimetric closure across the feed, concentrate and centrate streams showed that the centrifuge recovered 96.4 % of the culture biomass as a paste of 42 g L⁻¹ dry solids. For comparison, an alternative tangential-flow membrane harvest returned 91.8 % of the biomass, but tripled the processing time and delivered a more dilute concentrate that had to be centrifuged again before milling.\n\n' +
          'Bead milling used a 1.4 L horizontal chamber charged to 80 % of its free volume with 0.4 mm yttria-stabilised zirconia beads, operated in single-pass mode at feed rates between 12 and 40 L h⁻¹. The grinding chamber jacket was held at 12 °C throughout milling to limit thermal denaturation of released protein, and the outlet stream never exceeded 21 °C. High-pressure homogenisation used a two-stage valve at 1,200 bar, with the second stage set to one tenth of the first-stage pressure, and the product was cooled to the feed temperature between passes.\n\n' +
          'Disruption efficiency was scored as the loss of intact cells counted by flow cytometry after staining with a membrane-impermeant nucleic acid dye, referenced to an undisrupted control drawn from the same feed on the same day. Soluble protein in clarified lysate was quantified by the Lowry method against a bovine serum albumin standard curve prepared in the identical buffer, with every lysate diluted to fall in the middle third of the standard range. Bath sonication references were run at 20 kHz on 50 mL aliquots held on ice. All disruption conditions were run in triplicate from independent feed aliquots.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'A single pass through the bead mill at a tip speed of 12 m s⁻¹ disrupted 94.2 % of cells at a residence time of 3.5 min. Further increases in tip speed bought less than two percentage points at a disproportionate energy cost. Disruption rose steeply with residence time up to roughly 3 min and then flattened, consistent with a first-order population model in which a small subpopulation is markedly more resistant than the mean.\n\n' +
          'High-pressure homogenisation at 1,200 bar reached 88.6 % disruption in a single pass on the same feed. The gap between the two operations narrowed with repeated passes: three homogeniser passes raised disruption to 97.1 %, but specific energy demand rose 2.4-fold relative to the single-pass bead mill, and the lysate warmed by 9 °C across the three passes despite interstage cooling.\n\n' +
          'Protein release tracked cell counts closely for the bead mill and lagged behind them for the homogeniser. Soluble protein in the bead-milled lysate corresponded to 41.3 % DW by the Lowry assay, against 36.8 % DW for the single-pass homogenate. That difference is larger than the disruption scores alone would predict, and we attribute the excess to incomplete release of chloroplast-associated protein from cells whose plasma membrane has been permeabilised but whose internal compartments remain largely intact. Such cells are counted as disrupted by dye exclusion while contributing little to the soluble fraction.\n\n' +
          'Bath sonication, included as a laboratory reference, lysed only 61.5 % of cells after 20 min, at a specific energy input higher than either mechanical route required for near-complete disruption. Particle size distributions after milling showed a single mode near 1.1 µm with no residual population at the original cell diameter, whereas homogenates retained a persistent shoulder at 5 µm that co-eluted with intact cells in the cytometry gate. Overall recovery of soluble protein from culture to clarified lysate, taking harvest and disruption together, was 88 % for the bead-mill route.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The practical conclusion is narrower than a ranking of the two operations. For this feed, at this concentration and with this strain, bead milling reached a higher disruption score in one pass at lower specific energy, and its advantage came from the residence-time distribution of the stirred bed rather than from any difference in peak stress. The homogeniser can be pushed to the same score, but only by recirculating the product, which multiplies both the energy demand and the thermal load on the released protein.\n\n' +
          'That conclusion does not transfer automatically to a dilute feed. Bead mills are throughput-limited by residence time, so their energy per kilogram of dry biomass falls as the feed is concentrated, while homogeniser energy per unit volume is fixed by the operating pressure. A process that harvests to a thin slurry will see the ordering reverse. This is the main reason we report the harvest step alongside the disruption step: the two are coupled through feed concentration, and a disruption efficiency quoted without its feed concentration is not an interpretable number.\n\n' +
          'The divergence between cell counts and protein release deserves emphasis because it is a measurement artefact with economic consequences. A process designer who sizes a downstream train on dye-exclusion counts will over-predict the soluble protein entering the capture step. We suggest that disruption claims be reported against at least two orthogonal assays, and that the assay be named in any database record derived from them, since a single percentage carries no indication of which physical event it describes.\n\n' +
          'The limitations of this comparison are the single strain, the single feed concentration and the absence of a shear-sensitive product to act as a quality readout. Wall-deficient strains are the easy case; a walled reference strain would very likely widen the gap between the operations and might reverse the protein-release ordering. We also did not attempt to optimise the bead loading or the bead diameter, both of which are known to shift the energy optimum substantially, so the bead-mill figures should be read as a conservative baseline rather than as a best achievable performance.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-007',
    title:
      'Scale-up of Chlamydomonas reinhardtii cw15 from 2 L bubble columns to a 250 L flat-panel photobioreactor array',
    authors: [
      'Aleksy Ruminski',
      'Naledi Motaung',
      'Hyun-Woo Baek',
      'Celestine Dubourg',
      'Farhan Qureshi',
    ],
    year: 2022,
    venue: 'Photobioreactor Science and Engineering',
    organisms: ['cw15'],
    topics: ['photobioreactor', 'scale-up', 'light attenuation', 'co2 supply'],
    abstract:
      'Photoautotrophic scale-up is a light problem before it is a mixing or gas transfer problem, yet scale-up studies commonly hold volumetric power input constant and let the optical path vary. We transferred Chlamydomonas reinhardtii cw15 from 2 L bubble columns to a 250 L flat-panel array of eight 31 L panels, holding incident photon flux density, carbon supply and temperature to matched set points and constraining the optical path by construction. Growth, biomass density and carbon uptake were followed over nine-day batches in both systems, with light attenuation measured directly through the panel rather than inferred from biomass. The flat-panel array roughly doubled both the final biomass density and the mean volumetric productivity of the bubble columns at the same incident irradiance, and the improvement is fully accounted for by the shorter optical path and the higher frequency of light-dark cycling it imposes. Carbon limitation was excluded by operating at an enriched sparge composition and by closing the inorganic carbon balance across the gas and liquid phases. We report the reactor set points in full so that the productivity figures can be reused as design assumptions rather than as headline claims.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Scale-up of photoautotrophic culture is a light problem before it is a mixing or a gas transfer problem. As the optical path lengthens, the fraction of the reactor volume sitting below the compensation point grows, and the mean photon flux experienced by an average cell falls even when the incident flux at the surface is unchanged. A 2 L bubble column and a 250 L flat panel can be given identical incident irradiance and identical carbon supply and still return productivities differing by a factor of two, purely through attenuation and the light-dark cycling frequency that the geometry imposes.\n\n' +
          'Flat-panel geometries are attractive because the optical path is set by construction rather than by fluid dynamics. A panel of fixed thickness presents the same path length at 3 L and at 300 L, so the light regime can in principle be held invariant while volume is added by replicating panels rather than by enlarging one vessel. The cost of that invariance is a large illuminated surface area per unit volume, which raises the capital cost per litre and makes temperature control a first-order design concern rather than an afterthought.\n\n' +
          'Bubble columns remain the default at laboratory scale because they are cheap and easy to sterilise, and much of the kinetic data used to design larger systems originates in them. Transferring those data upward requires knowing which of the observed rates were set by the organism and which were set by the vessel. A specific growth rate measured in a thin, well-illuminated column is a property of the strain under those conditions; a volumetric productivity measured in the same column is a property of the column.\n\n' +
          'We therefore designed the transfer to hold the light and carbon boundary conditions matched, and to measure attenuation directly through the panel rather than to infer it from biomass concentration and a literature extinction coefficient. The intention was to produce productivity figures that can be reused as design assumptions with their conditions attached, and to report the full set of reactor set points alongside them.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'The flat-panel array comprised eight polycarbonate panels of 31 L working volume each, with a 30 mm optical path, mounted in two rows of four and operated in parallel from a common medium reservoir. The reference system was a set of four 2 L glass bubble columns of 60 mm diameter. Both systems were inoculated to an optical density at 750 nm of 0.12 from the same seed culture of Chlamydomonas reinhardtii cw15, grown photoautotrophically in a nitrate-based minimal medium.\n\n' +
          'Panels were illuminated on both faces by dimmable white LED arrays at an incident photon flux density of 420 µmol m⁻² s⁻¹, measured at the panel surface with a spherical quantum sensor before inoculation and again after each batch. The 2 L bubble columns received 180 µmol m⁻² s⁻¹ at the vessel surface, chosen so that the volumetric photon supply per litre of culture matched the panels to within four per cent despite the different surface-to-volume ratios.\n\n' +
          'Sparge gas was blended to 2.5 % v/v CO2 and delivered at 0.15 vvm through a sintered stainless-steel diffuser at the base of each panel. In the reference system the bubble columns were sparged with air enriched to 1.0 % v/v CO2 at the same superficial gas velocity, which was the highest enrichment the columns could accept without foaming over. Inlet and outlet gas composition was logged continuously by infrared analysis, and dissolved inorganic carbon was measured twice daily so that the carbon balance could be closed across both phases.\n\n' +
          'Culture temperature was maintained at 25.0 °C by a jacketed water loop on the rear panel face, with the set point held during both the illuminated and the dark period. The pH set point of 7.0 was maintained by on-demand injection of the CO2-enriched gas against a dead band of 0.1 units, and pH was logged at one-minute intervals. Biomass was sampled twice daily for optical density at 750 nm and for gravimetric dry cell weight, and light transmission through the panel was recorded at the same times with a fixed sensor mounted on the far face.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Both systems left lag within twelve hours of inoculation and entered a light-limited linear phase by day three, after which biomass accumulated at a constant rate rather than exponentially. Mean volumetric productivity over the linear growth phase was 0.048 g L⁻¹ h⁻¹ in the flat-panel array, calculated from the gravimetric dry cell weight series between day three and day eight and confirmed by the integrated carbon uptake over the same window.\n\n' +
          'The flat-panel array reached a final biomass density of 3.8 g L⁻¹ on day 9, at which point transmission through the panel had fallen below two per cent and the productivity had begun to decline. Under matched incident irradiance and matched volumetric photon supply, the bubble columns plateaued at 2.1 g L⁻¹ and did so two days earlier, despite receiving the same photons per litre. Panel surface temperature never exceeded the 25.0 °C set point during the illuminated period, and the rear-face jacket removed a peak thermal load of 1.1 kW across the array at midday equivalent.\n\n' +
          'The carbon balance closed to within six per cent in the panels across all four batches. Off-gas analysis showed that carbon uptake tracked the biomass accumulation rate with no lag, and the dissolved inorganic carbon concentration never fell below 0.4 mmol L⁻¹, which we take as sufficient evidence that carbon was not the limiting substrate at any point. In the bubble columns the dissolved inorganic carbon pool was drawn down further during the illuminated period, but recovered overnight and did not limit the observed rates.\n\n' +
          'Direct transmission measurements separated the two contributions to the productivity difference. At equal biomass concentration the panels transmitted six times more light to the far face than the columns, and the calculated mean photon flux per cell in the panels remained above the compensation point until day eight, whereas in the columns it crossed below on day six. Pigment content per gram of dry weight rose in both systems as the cultures self-shaded, but rose more steeply in the columns, which is the expected acclimation response and further reduced the transmitted flux there.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The doubling of both final density and mean productivity is fully accounted for by geometry. Once the incident flux and the volumetric photon supply are matched, the only remaining differences between the systems are the optical path and the resulting frequency at which a circulating cell passes between the illuminated and the dark zone. Our transmission data support the simple interpretation: the panel keeps a larger fraction of its volume above the compensation point for longer, and it delays the onset of the light-limited plateau by two days.\n\n' +
          'This has a direct consequence for how kinetic parameters should be reused. A specific growth rate measured during the brief exponential window is transferable between the two systems, and ours agreed to within the measurement error. A volumetric productivity is not transferable, because it is a property of the reactor geometry as much as of the organism, and it should never be carried from a laboratory column into a plant design without an explicit attenuation correction.\n\n' +
          'Productivities as high as 0.075 g L⁻¹ h⁻¹ have been claimed for outdoor tubular systems, though rarely with a closed carbon balance and rarely averaged over a whole batch rather than over the best day. We are cautious about such comparisons for two reasons. First, an instantaneous productivity measured at the peak of the linear phase can exceed the batch mean by fifty per cent. Second, outdoor systems experience a diel light cycle that our constant-illumination panels do not, so a like-for-like comparison would require an integrated daily photon dose rather than an instantaneous flux.\n\n' +
          'The main limitation of this work is that it was carried out under constant artificial illumination at a single temperature. Diel cycling introduces night-time biomass loss that our batches do not exhibit, and outdoor thermal swings would place a much heavier duty on the temperature control loop than the 1.1 kW peak we measured. We also did not test panel spacing, which sets the mutual shading between rows and is the dominant term in the areal productivity of any real installation.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-008',
    title:
      'A cross-strain survey of total protein in Chlamydomonas reinhardtii: Lowry and Kjeldahl estimates diverge under nitrogen limitation',
    authors: [
      'Beatriz Nogueira Salles',
      'Tomasz Wiercinski',
      'Amara Okonjo',
      'Sun-Hee Pak',
      'Etienne Marchildon',
    ],
    year: 2019,
    venue: 'Algal Biochemistry Reports',
    organisms: ['cw15', 'cc1690'],
    topics: ['protein content', 'lowry assay', 'kjeldahl', 'nitrogen limitation'],
    abstract:
      'Protein content is the headline compositional figure for microalgal biomass intended as feed or food, and it is quoted as though it were a single measurable quantity. It is not. We surveyed two laboratory strains of Chlamydomonas reinhardtii, the wall-deficient cw15 and the walled wild-type isolate cc1690, under nitrogen-replete and nitrogen-limited conditions, measuring total protein in the same freeze-dried biomass by the Lowry colorimetric assay and by Kjeldahl nitrogen determination with a fixed nitrogen-to-protein factor. The two methods agreed to within eight percentage points under nitrogen-replete conditions but diverged sharply under limitation, where accumulated nitrate and free amino acids inflate the Kjeldahl estimate while the colorimetric assay follows the true polypeptide pool. cc1690 was consistently richer in protein than cw15 at matched growth phase. We argue that any database record of protein content is uninterpretable without the assay, the growth phase and the nitrogen status attached to it, and we report all three for every figure given here so that the values can be reused with their conditions intact.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Protein content is the headline compositional figure for microalgal biomass destined for feed or food applications, and it is routinely quoted as a single number with a single unit. That practice obscures a real methodological divergence. The two dominant assays measure different things: the Lowry colorimetric method responds principally to peptide bonds and to a small set of aromatic and sulphur-containing residues, whereas Kjeldahl digestion measures total reduced nitrogen and converts it to protein through a fixed factor that assumes a constant nitrogen fraction of the protein pool.\n\n' +
          'Under balanced growth those assumptions hold well enough that the two methods agree within the uncertainty of either. Under nitrogen limitation they do not. Cells accumulate nitrate in the vacuole, and the free amino acid pool expands and contracts on a timescale much shorter than the protein pool. Both effects add nitrogen that is not in polypeptide, so the Kjeldahl figure rises relative to the colorimetric one, in the same direction and by a variable amount that depends on how the culture was starved and for how long.\n\n' +
          'The choice of strain compounds the problem. Wall-deficient mutants such as cw15 lack much of the hydroxyproline-rich glycoprotein wall of the wild type, so a given mass of dry biomass contains a different ratio of soluble to structural protein, and the extraction efficiency of the colorimetric assay differs accordingly. Comparisons drawn across strains and across assays therefore carry two confounds at once, and the literature contains few surveys that control both.\n\n' +
          'We set out to quantify the divergence directly by applying both assays to the same freeze-dried biomass, from both strains, at matched growth phase, under nitrogen-replete and nitrogen-limited conditions. Our aim is not to declare one assay correct. It is to establish how large the disagreement becomes under conditions that are common in production, and to make the case that a protein content is not a portable datum unless the assay, the growth phase and the nitrogen status travel with it.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Chlamydomonas reinhardtii cw15 and cc1690 were maintained in Tris-acetate-phosphate medium and transferred to a nitrate-limited minimal medium for the experimental cultures. Nitrogen-replete cultures received 7.5 mmol L⁻¹ nitrate; nitrogen-limited cultures were grown to mid-exponential phase in the same medium, harvested by centrifugation, washed twice in nitrogen-free medium and resuspended without a nitrogen source for a further 72 h. All cultures were grown at 25 °C under 120 µmol m⁻² s⁻¹ of continuous illumination in shaken flasks.\n\n' +
          'Biomass was sampled at mid-exponential phase and at the end of the starvation period, collected by centrifugation, washed twice in ammonium formate, frozen at -80 °C and freeze-dried to constant mass. Every compositional figure reported here derives from the same freeze-dried powder, subsampled for the two assays, so that no part of the divergence can be attributed to differences in harvest or storage. cc1690 cultures reached 1.9 g L⁻¹ dry cell weight at the point of sampling, and cw15 cultures reached a comparable density within the same window.\n\n' +
          'The Lowry assay was performed on an alkaline extract of the freeze-dried powder, with 20 min of extraction at 60 °C in sodium hydroxide before neutralisation, against a bovine serum albumin standard curve prepared in the same matrix. Extraction efficiency was checked by re-extracting the pellet and assaying the second extract, which contained less than three per cent of the first in all cases. Kjeldahl determinations used sulphuric acid digestion with a copper catalyst, followed by steam distillation and titration; a nitrogen-to-protein factor of 6.25 was applied to all Kjeldahl estimates, without adjustment for strain or nitrogen status.\n\n' +
          'Nitrate carried over in the biomass was measured separately on a matched subsample by ion chromatography of an aqueous extract, so that its nitrogen contribution to the Kjeldahl figure could be estimated independently. All assays were run in quadruplicate on biological triplicates, and the reported figures are means across biological replicates.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Under nitrogen-replete conditions the two assays agreed reasonably well. Nitrogen-replete cw15 contained 38.4 % DW protein by the Lowry assay, and the same biomass returned 46.1 % DW by Kjeldahl digestion, a gap of just under eight percentage points that is consistent with the known contribution of nucleic acid nitrogen and residual medium salts to the total nitrogen pool.\n\n' +
          'The walled wild-type strain was richer in protein than the wall-deficient mutant at matched growth phase. cc1690 was consistently richer, at 42.7 % DW by Lowry, and 49.5 % DW by Kjeldahl on the same freeze-dried powder. The ordering between strains was preserved by both assays and across all three biological replicates, so we regard the strain difference as robust even though its absolute size depends on which assay is quoted. Mid-exponential cw15 biomass contained 31.2 % DW protein by Lowry when sampled two days earlier in the growth curve, which illustrates how much of the apparent spread in published values is simply growth-phase variation.\n\n' +
          'Nitrogen limitation broke the agreement between the methods. After 72 h of nitrogen starvation the Lowry estimate for cw15 fell to 21.6 % DW, tracking the expected degradation of the photosynthetic apparatus and the accumulation of storage carbohydrate that dilutes every other component of the dry weight. The Kjeldahl estimate for the same biomass fell far less, and independent ion chromatography accounted for roughly a third of the residual difference as vacuolar nitrate that had been carried through the wash steps.\n\n' +
          'The divergence was directional and reproducible in both strains. In every nitrogen-limited sample the Kjeldahl figure exceeded the colorimetric figure by more than it did in the matched replete sample, and the excess grew with the duration of starvation over the interval we sampled. We did not observe the reverse ordering in any sample, which argues against the divergence being driven by incomplete alkaline extraction of the colorimetric assay under starvation conditions.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The practical message is that a protein content is a measurement, not a property. Two competent laboratories applying two standard assays to a single homogeneous powder will report values that differ by eight percentage points under favourable conditions and by considerably more under nitrogen limitation, and neither is making an error. The number is only interpretable when the assay is named alongside it.\n\n' +
          'This matters most where the values are reused rather than where they are generated. A feed formulation, a process economic model or a database of strain characteristics will typically ingest a single figure with a percentage sign and no methodological context. If those figures are drawn from a mixture of colorimetric and nitrogen-based determinations, the resulting spread will be read as biological variation between strains when much of it is assay variation within a single sample. Our cross-strain comparison is only defensible because both strains were measured by both methods on the same day from the same powder.\n\n' +
          'The fixed nitrogen-to-protein factor deserves particular scrutiny. It was derived for terrestrial plant material with a very different nitrogen distribution, and applying it unchanged to microalgal biomass under nitrogen limitation is close to indefensible: the very condition that raises non-protein nitrogen is the condition under which the factor is most often applied. Strain-specific and condition-specific factors have been proposed, but they require an amino acid analysis that few laboratories run routinely, and adopting a variable factor would break comparability with the historical record.\n\n' +
          'We recommend that protein content be reported with the assay, the growth phase and the nitrogen status of the culture, and that database records carry those three attributes as first-class fields rather than as free-text notes. The limitations of this survey are its two laboratory strains, its single light intensity and its single starvation duration; a production strain grown outdoors under a diel cycle would sample a far wider range of nitrogen states than we imposed here.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-009',
    title:
      'Acetate-limited fed-batch cultivation of Chlamydomonas reinhardtii cw15 raises biomass yield without a pigment penalty',
    authors: [
      'Helene Tremaux',
      'Yusuf Abdulkarim Danladi',
      'Petra Sandoval Rios',
      'Nikolai Grebenshchikov',
    ],
    year: 2023,
    venue: 'Fermentation and Bioprocess Letters',
    organisms: ['cw15'],
    topics: ['fed-batch', 'mixotrophic growth', 'acetate feeding', 'biomass yield'],
    abstract:
      'Mixotrophic cultivation of Chlamydomonas reinhardtii on acetate is fast but wasteful: batch cultures started at a growth-permissive acetate concentration overflow carbon to the medium and bleach as acetate accumulates relative to demand. We implemented an acetate-limited fed-batch in which the feed rate was slaved to the measured off-gas carbon dioxide evolution rate, holding residual acetate below the detection limit throughout the feed phase. Growth rate, biomass yield on acetate, final biomass density and pigment content were compared against an uncontrolled batch reference on the same medium and at the same illumination. The fed-batch raised biomass yield on acetate by a quarter and quadrupled final biomass density relative to the batch, while chlorophyll per gram of dry weight was statistically indistinguishable between the two processes at harvest. Protein-specific productivity was sustained across the entire feed phase rather than decaying after the first day, as it did in the batch. We report the control law, the feed composition and every derived kinetic parameter so that the process can be reproduced or scaled.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Acetate is the standard organic carbon source for Chlamydomonas reinhardtii, and mixotrophic cultures on acetate grow several times faster than photoautotrophic ones at the same light intensity. The convenience comes at a cost that is easy to overlook in flask culture. Acetate is a weak acid and an uncoupler at elevated concentration, and cultures started at a growth-permissive concentration are exposed to their highest acetate load precisely when their biomass, and therefore their uptake capacity, is lowest.\n\n' +
          'The consequences are visible as a yield loss and as pigment bleaching. Carbon taken up in excess of anabolic demand is respired or excreted, so the observed biomass yield on acetate in batch culture falls well below the value that carbon and energy balances predict. Bleaching follows from the same imbalance, because a cell that is carbon-replete and light-saturated down-regulates its antenna and, at the extreme, degrades it. Neither effect is a property of the organism; both are properties of how the carbon was delivered.\n\n' +
          'Fed-batch operation addresses this directly by supplying acetate at the rate the culture can consume it, so that the residual concentration in the broth stays close to zero and the specific uptake rate is set by the feed rather than by the medium composition. The difficulty is choosing the feed law. A pre-programmed exponential feed requires an accurate estimate of the growth rate and fails ungracefully if the culture deviates from it; a feedback law needs an online measurement that responds fast enough to be useful.\n\n' +
          'We chose the carbon dioxide evolution rate from off-gas analysis as the feedback signal, because it responds within minutes to a change in metabolic demand and because it is already instrumented on most fermenters. This paper reports the resulting process, its kinetics and its yields, against an uncontrolled batch reference run on the same medium at the same illumination, and gives the parameters in enough detail to be reused as design inputs.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Chlamydomonas reinhardtii cw15 was cultivated in a 15 L stirred-tank bioreactor with a 10 L working volume, illuminated externally by LED panels delivering 150 µmol m⁻² s⁻¹ at the vessel surface. The batch medium was a modified Tris-acetate-phosphate formulation containing 1.0 g L⁻¹ sodium acetate at inoculation, with phosphate and trace elements in fourfold excess of the batch requirement so that neither could become limiting during the feed phase.\n\n' +
          'The feed reservoir contained sodium acetate at 30.0 g L⁻¹, sterilised separately from the ammonium and phosphate feeds to avoid precipitation, and was delivered by a calibrated peristaltic pump under gravimetric verification. Feed rate was slaved to the carbon dioxide evolution rate computed from paramagnetic oxygen and infrared carbon dioxide analysis of the off-gas, with the proportionality constant set from the stoichiometric acetate demand and updated once at the start of the feed phase. Residual acetate was measured every four hours by enzymatic assay and remained below the 0.05 g L⁻¹ detection limit for the whole feed phase.\n\n' +
          'Temperature was controlled at 25 °C and pH at 7.2 by addition of dilute sulphuric acid only, since acetate consumption drives the pH upward in this system. Dissolved oxygen was held above thirty per cent of saturation by cascade to agitation, with the sparge rate fixed at 0.2 vvm of air. The batch reference was run in the same vessel under identical light, temperature and pH control, but received its entire carbon charge at inoculation as 8.0 g L⁻¹ sodium acetate.\n\n' +
          'Biomass was followed by optical density at 750 nm and by gravimetric dry cell weight on filtered, washed and oven-dried samples taken every eight hours. Total protein was determined by the Lowry method on freeze-dried biomass, and chlorophyll a and b were extracted in methanol and quantified spectrophotometrically. Biomass yield on substrate was computed from the cumulative gravimetric acetate addition and the total dry biomass formed, corrected for the sampling volume removed over the run.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Mixotrophic batch cultures grew at 0.094 h⁻¹ during the first 36 h, close to the maximum reported for this strain on acetate, while photoautotrophic controls grew at 0.038 h⁻¹ under the same illumination without an organic carbon source. The exponential fit for the mixotrophic culture was excellent over that window, and the observed doubling time of 7.4 h is consistent with the fitted rate to within the precision of the gravimetric series.\n\n' +
          'Yields separated the two processes more sharply than rates did. Biomass yield on acetate over the feed phase was 0.41 g g⁻¹, whereas the uncontrolled batch reference returned only 0.33 g g⁻¹ across the whole run. The difference appeared in the second half of the batch, where residual acetate accumulated above 2 g L⁻¹ and the instantaneous yield fell steeply, and it is consistent with overflow respiration of carbon taken up faster than it could be committed to biomass.\n\n' +
          'The fed-batch process finished at 8.6 g L⁻¹ dry cell weight after 118 h, against 2.2 g L⁻¹ for the batch reference, which had exhausted its acetate charge by 60 h and grew only photoautotrophically thereafter. Over the 60 h feed phase this corresponds to a volumetric productivity of 0.11 g L⁻¹ h⁻¹, sustained without decline until the feed was stopped. Protein-specific productivity averaged 14.7 mg g⁻¹ h⁻¹ across the feed phase, and its stability is the clearest single indicator that the culture remained carbon-limited rather than carbon-saturated.\n\n' +
          'Pigment content did not pay for the higher biomass. Chlorophyll a plus b at harvest was 21.4 mg g⁻¹ of dry weight in the fed-batch and 20.8 mg g⁻¹ in the batch, a difference well inside the replicate spread. Visual bleaching, which was pronounced in the batch reference between 30 and 50 h when residual acetate was highest, did not occur at any point in the fed-batch. The chlorophyll a to b ratio was likewise unchanged, indicating that antenna size was not reduced under the fed-batch regime.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The yield improvement and the absence of bleaching have the same cause, and it is a control result rather than a biological one. Holding residual acetate below the detection limit keeps the specific uptake rate at or below the rate at which carbon can be committed to biomass, which removes both the overflow loss and the carbon-saturated state that triggers antenna down-regulation. Nothing about the strain changed; only the delivery of the substrate did.\n\n' +
          'Slaving the feed to carbon dioxide evolution proved more robust than we expected. The signal responds within minutes, which is fast relative to the acetate uptake timescale, and it degrades gracefully: a sensor drift produces a slow feed offset that shows up in the residual acetate assay long before it destabilises the culture. A pre-programmed exponential feed on the same vessel overshot twice in preliminary runs and required manual intervention both times.\n\n' +
          'For process design the important figure is the yield rather than the density. A fed-batch that reaches 8.6 g L⁻¹ without any pigment penalty also consumes a quarter less acetate per kilogram of biomass than the batch, and in most cost models the substrate line is larger than the reactor line at this scale. The productivity figure should be treated with more care, since it is bounded here by the light supply of our vessel and would change in a reactor with a different optical path.\n\n' +
          'Two limitations bound these conclusions. We ran a single feed composition and a single light intensity, so the interaction between light supply and the maximum sustainable feed rate is unresolved, and it is precisely that interaction that will set the ceiling on scale-up. We also stopped the feed at 118 h for operational reasons rather than because the culture had stopped responding, so the reported final density is not a true maximum for the process.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-010',
    title:
      'Wavelength choice and growth phase dominate the error in optical-density-to-dry-weight calibration for green microalgae',
    authors: [
      'Marisol Etxebarria',
      'Chidi Nwakanma',
      'Anneke Vosloo',
      'Ryosuke Hatanaka',
    ],
    year: 2020,
    venue: 'Methods in Bioprocess Analytics',
    organisms: ['cw15', 'cc1690'],
    topics: ['od750 calibration', 'dry cell weight', 'analytical methods'],
    abstract:
      'Optical density is the most frequently measured quantity in microalgal cultivation and the least frequently calibrated. Growth curves, productivities and yields are routinely computed from a conversion factor taken from another laboratory, another strain or another wavelength. We measured optical-density-to-dry-weight factors for Chlamydomonas reinhardtii cw15 and cc1690 across the linear range of a standard spectrophotometer, at 750 nm and at 680 nm, in exponential and stationary phase, with gravimetric dry cell weight determined in quadruplicate against a washed and dried filter blank. The factor is strain-specific, wavelength-specific and phase-specific, and the spread across those three variables exceeds thirty per cent, which is larger than most of the process differences the factor is used to detect. Measurement at 680 nm is contaminated by chlorophyll absorbance and drifts with pigment content, so it should not be used for biomass estimation at all. We give the factors with their confidence intervals, the linear range over which each holds, and a short protocol for laboratories that need to derive their own.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Optical density is the workhorse measurement of microalgal cultivation. It is fast, it consumes a millilitre of culture, it needs no consumables, and it can be read by an instrument that most laboratories already own. It is also not a measurement of biomass. Optical density at a given wavelength reports the attenuation of a collimated beam by scattering and absorbance combined, and the relationship between that attenuation and the dry mass of cells in the cuvette depends on cell size, cell shape, refractive index, pigment content and the acceptance angle of the detector.\n\n' +
          'In practice a conversion factor is applied, and in practice that factor is very often borrowed. It is taken from a previous paper on a different strain, or from a supplier note, or from a calibration performed years earlier on a different instrument. Because the borrowed factor is applied consistently within a study, internal comparisons remain valid and the error is invisible to the authors. It becomes visible only when the resulting biomass concentrations, productivities and yields are compared across laboratories, or ingested into a database that treats them as commensurable.\n\n' +
          'The wavelength convention compounds this. Readings at 750 nm are preferred because chlorophyll absorbs weakly there, so the signal is dominated by scattering and is comparatively insensitive to pigment content. Readings at 680 nm sit near the chlorophyll a absorption maximum and therefore respond strongly to both biomass and pigmentation, which makes them useful as a pigment proxy and unsuitable as a biomass proxy. Both are reported in the literature, and the wavelength is not always stated.\n\n' +
          'We set out to quantify how much the conversion factor actually moves across the variables a working laboratory is likely to encounter: two strains, two wavelengths and two growth phases. Our purpose is to give reusable factors with their conditions and confidence intervals attached, and to show that borrowing a factor across any one of these variables introduces an error comparable to the process effects the measurement is usually deployed to detect.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Chlamydomonas reinhardtii cw15 and cc1690 were grown in Tris-acetate-phosphate medium in shaken flasks. Maintenance cultures were held under continuous illumination at 90 µmol m⁻² s⁻¹ and subcultured weekly, and experimental cultures were inoculated from these at a fixed ratio to standardise physiological history. Exponential-phase biomass was harvested at the midpoint of the logarithmic phase and stationary-phase biomass 48 h after the growth rate had fallen below a tenth of its maximum.\n\n' +
          'Calibration standards were prepared by concentrating culture and diluting it stepwise into spent, cell-free medium from the same flask, so that the optical background of the suspending fluid was matched to the sample. The dilution series spanned optical densities at 750 nm from 0.05 to 0.85 in eleven steps, and the highest calibration standard, 1.2 g L⁻¹, was verified independently against an undiluted concentrate. All optical densities were read in 10 mm path-length cuvettes against a spent-medium blank, with samples inverted immediately before reading.\n\n' +
          'Dry cell weight was determined in quadruplicate for every standard. A 25 mL aliquot was filtered onto a pre-washed, pre-dried and pre-weighed glass-fibre filter of 0.7 µm nominal retention, washed twice with an equal volume of ammonium formate isotonic with the medium, and dried at 105 °C to constant mass. Filter blanks were carried through the identical wash and dry cycle and subtracted, which removes the largest single source of bias at the dilute end of the series.\n\n' +
          'Factors were obtained by ordinary least squares regression of dry cell weight on optical density through the origin, restricted to the range over which the residuals showed no curvature. Confidence intervals are reported at the ninety-five per cent level from the regression. Linearity was assessed by fitting the unrestricted model with an intercept and testing whether the intercept differed from zero; in all cases it did not, once the filter blank had been subtracted correctly.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'For cw15 the OD750-to-DCW factor was 0.42 g L⁻¹ OD⁻¹ over the linear range, with a ninety-five per cent confidence interval of 0.40 to 0.44 and no detectable curvature below an optical density of 0.85. Above that value the residuals turned systematically negative, which is the expected consequence of multiple scattering, and dilution into spent medium was required to bring readings back into the valid range.\n\n' +
          'The walled wild-type strain differed materially. cc1690 required a higher factor of 0.47 g L⁻¹ OD⁻¹ over the same optical range, and the difference between the two strains is larger than the confidence interval of either. We attribute it to the glycoprotein wall, which adds dry mass without adding a proportionate amount of scattering cross-section, so a gram of cc1690 biomass is optically quieter than a gram of cw15 biomass.\n\n' +
          'Wavelength mattered more than strain. At 680 nm the same biomass gave 0.31 g L⁻¹ OD⁻¹, with pigment absorbance inflating the optical reading and therefore depressing the apparent factor. Worse, the 680 nm factor was not stable: it fell by a further eleven per cent in cultures acclimated to low light, which have a larger antenna per unit biomass, whereas the 750 nm factor was unchanged between those cultures within the measurement error.\n\n' +
          'Growth phase introduced a comparable shift. Stationary-phase cw15 cells required 0.55 g L⁻¹ OD⁻¹, a 31 % increase over exponential cells, reflecting the accumulation of dense storage carbohydrate that adds mass faster than it adds scattering cross-section. Taken together, the spread across strain, wavelength and phase exceeds thirty per cent of the central value, which is larger than most of the process differences that a growth curve is deployed to resolve.',
      },
      {
        id: 's4',
        heading: 'Practical guidance and discussion',
        text:
          'Three recommendations follow directly from these data. Read biomass at 750 nm and not at 680 nm, because the 680 nm signal is a mixture of biomass and pigmentation and drifts with acclimation state even when biomass is constant. Keep readings below an optical density of about 0.85 and dilute into spent, cell-free medium rather than into fresh medium or water, both of which change the refractive index of the suspending fluid and the osmotic state of the cells. Subtract a filter blank carried through the identical wash and dry cycle, since at the dilute end of the series the blank is a substantial fraction of the measured mass.\n\n' +
          'The cw15 factor of 0.42 g L⁻¹ OD⁻¹ should not be transferred between strains without re-calibration. It should also not be transferred between growth phases, and a study that computes a productivity from exponential-phase optical densities and a harvest density from stationary-phase optical densities using one factor will bias the two ends of its growth curve in opposite directions. Where a single factor must be used for a whole batch, the exponential-phase value is the safer choice, because most of the integrated growth occurs while the cells are in that state.\n\n' +
          'Deriving a local factor is not onerous. An eleven-point dilution series with quadruplicate gravimetric determination occupies one working day and one litre of culture, and it needs repeating only when the strain, the instrument or the medium changes. We consider that a small cost against a systematic error of a third in every biomass figure a laboratory subsequently reports.\n\n' +
          'The limitations are the instrument geometry and the medium. Spectrophotometers differ in acceptance angle, and an instrument that collects more forward-scattered light will report a lower optical density for the same suspension, so factors are not strictly portable between instruments either. We also worked exclusively in a single defined medium; a high-salt or high-turbidity medium would change the blank and probably the linear range as well.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-011',
    title:
      'A transparent costing framework for microalgal biomass: harmonising yield, recovery and productivity assumptions across published process designs',
    authors: [
      'Oluwaseun Adebanjo-Ferreira',
      'Katarzyna Milewska',
      'Rahul Venkataraman Iyer',
      'Fenna de Ruiter',
      'Tevita Ratuvou',
    ],
    year: 2024,
    venue: 'Bioprocess Economics and Systems Analysis',
    organisms: ['cw15', 'aplat'],
    topics: ['techno-economic analysis', 'process modelling', 'harvest recovery', 'assumption harmonisation'],
    abstract:
      'Published minimum selling prices for microalgal biomass span more than an order of magnitude, and the spread is usually attributed to scale or to geography. We show that most of it is attributable to three assumptions that are rarely stated together: biomass yield on substrate, harvest recovery and the biomass density delivered at harvest. We present a costing framework in which every physical assumption is declared with its provenance, its unit and the operating condition it was measured under, and in which cost lines are computed per kilogram of dry biomass so that they sum to the headline figure by construction. Applying the framework to a harmonised baseline for a closed photobioreactor train and an open raceway, we find that the choice of harvest technology moves the delivered cost more than a twofold difference in reactor capital cost does. The framework is intended to make assumptions auditable rather than to produce a single number, and we identify the parameters whose measurement uncertainty dominates the result.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Techno-economic assessments of microalgal biomass disagree with one another by more than an order of magnitude in the minimum selling price they report. The disagreement is commonly explained by differences in scale, location, product specification or the year of the cost basis. Those factors matter, but they do not account for the spread. Two studies of the same product at the same scale in the same year can differ by a factor of five, and when their assumptions are unpacked the difference resolves into a handful of physical parameters that each study adopted from a different source without stating the operating conditions those sources measured under.\n\n' +
          'Three parameters do most of the work. Biomass yield on substrate sets the largest variable cost line in any heterotrophic or mixotrophic design. Harvest recovery multiplies straight through to the delivered mass and is frequently assumed rather than measured, often at a value that no continuous separation actually achieves. Biomass density at harvest sets the volume that the downstream train must process per kilogram of product, and therefore drives both the capital cost and the energy demand of dewatering.\n\n' +
          'These parameters are not independent of one another, and treating them as separately adjustable dials produces combinations that are physically unattainable. A design that assumes a high biomass density at harvest and simultaneously assumes the recovery of a technology validated only on dilute feeds is internally inconsistent, but nothing in a conventional spreadsheet flags that inconsistency, and the resulting selling price is reported with the same confidence as any other.\n\n' +
          'We propose a framework in which every physical assumption is declared with its value, its unit, the operating condition under which it was measured and a pointer to its source, and in which the cost model is required to compute all lines per kilogram of dry biomass so that they sum to the headline by construction. The intention is not to produce a better number. It is to make the number auditable, so that a reader can see which assumption a conclusion rests on and replace it with their own.',
      },
      {
        id: 's2',
        heading: 'Framework and methods',
        text:
          'The framework separates three layers. The assumption register holds every physical parameter with its value, unit, measurement condition and provenance class, where provenance is one of measured in a cited study, derived from a declared calculation, or an engineering estimate with no literature ancestry. The process model maps those assumptions onto mass and energy flows for a defined train of unit operations. The cost model converts flows into cost lines, all expressed per kilogram of dry biomass delivered at the battery limit, so that the lines sum to the headline figure with no residual term.\n\n' +
          'Requiring per-kilogram cost lines is a deliberate constraint. It forbids the common practice of computing capital cost per unit reactor volume and revenue per unit product mass, then reconciling them with a utilisation factor that absorbs any arithmetic that does not close. In our formulation the utilisation factor appears explicitly in the assumption register and is visible to sensitivity analysis like any other parameter.\n\n' +
          'The harmonised baseline assumes a biomass yield on acetate of 0.45 g g⁻¹, taken from fed-batch cultivation under acetate limitation rather than from batch culture, on the grounds that no plant would be operated in a regime that discards a quarter of its carbon. Where a source reported a batch yield we did not adjust it upward; we excluded it and noted the exclusion, since a silently corrected assumption is worse than an absent one.\n\n' +
          'Two reference trains are modelled. The closed train is a flat-panel photobioreactor array feeding a disc-stack centrifuge and a bead mill; the open train is a raceway pond feeding gravity settling and dissolved-air flotation before centrifugation. Both are modelled at a nominal 500 tonne per year dry biomass output. Sensitivity is evaluated by one-at-a-time perturbation of each register entry across its stated measurement uncertainty, and by a joint perturbation of the parameter pairs we identify as physically coupled.',
      },
      {
        id: 's3',
        heading: 'Baseline results',
        text:
          'The two trains are separated less by their reactors than by their separations. In the closed train, a photobioreactor array delivering 4.8 g L⁻¹ at harvest presents the downstream section with a manageable volume, and disc-stack centrifugation is credited with 92.0 % harvest recovery in the baseline, taken from a pilot-scale gravimetric closure rather than from a vendor specification. The combination puts the dewatering energy demand well below the cultivation energy demand.\n\n' +
          'The open train inverts that balance. A raceway operating at a biomass density an order of magnitude lower must process roughly ten times the volume per kilogram of product, and no single separation handles that economically. Settling followed by dissolved-air flotation recovers 78.5 % of Arthrospira platensis biomass in the baseline, and the surviving stream still requires centrifugation to reach a paste. Harvest is the largest single cost line in the open train and the third largest in the closed one.\n\n' +
          'Sensitivity analysis ranks the assumptions unambiguously. Harvest recovery and biomass density at harvest dominate, jointly accounting for more than half of the variance in the delivered cost across the stated uncertainty ranges, followed by biomass yield on substrate. Reactor capital cost per unit volume, which receives the most attention in the literature and in vendor discussions, ranks fourth: doubling it moves the headline by less than a twenty per cent change in harvest recovery does.\n\n' +
          'The coupled perturbations matter. Perturbing harvest recovery and harvest biomass density independently produces a wider apparent uncertainty band than perturbing them jointly along their physically realisable locus, because the technologies that achieve high recovery on dilute feeds are the ones with the highest specific energy demand. A one-at-a-time sensitivity analysis therefore overstates the accessible design space, and every published range we examined was produced that way.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The framework does not make a techno-economic assessment correct. It makes it auditable, which is a different and more achievable goal. A reader who disagrees with our harvest recovery can see exactly which line it feeds, replace it and recompute, and a reader who wants to know whether a headline rests on a measured value or on an engineering estimate can see that from the provenance class without reading the methods section.\n\n' +
          'We think the provenance class is the most transferable part of this work. In our own baseline, seven of the twenty-two register entries have no literature ancestry at all; they are estimates we made because no measurement exists. That proportion is not unusual, and it is not a criticism of the field, but it is invisible in a conventional assessment where a measured yield and an invented utilisation factor appear in the same table in the same typeface. Marking the difference costs nothing and changes how the result is read.\n\n' +
          'The ranking of harvest above reactor capital is the substantive finding, and it has a straightforward implication for research allocation. Effort spent raising the biomass density delivered to the separation, whether by reactor design or by cultivation strategy, propagates through the entire downstream train, whereas effort spent reducing reactor capital cost per litre touches one line. The parameters that most need better measurement are the ones we currently assume most freely.\n\n' +
          'Several limitations apply. The framework is only as good as the register behind it, and we have populated ours from a deliberately narrow set of studies that report their operating conditions in full, which biases it toward well-instrumented pilot work and away from production experience. We model a single output scale, and the separations do not scale linearly. Finally, we make no attempt to price the product, so the framework returns a cost of delivered biomass rather than a viability judgement.',
      },
    ],
    ingest: 'complete',
  },
];

export const RECORDS_B: ExtractionRecord[] = [
  // ---------------------------------------------------------------- SP-006
  {
    id: 'ex-0043',
    paperId: 'SP-006',
    sectionId: 's3',
    quote: 'a tip speed of 12 m s⁻¹ disrupted 94.2 % of cells',
    field: 'disruption_efficiency',
    value: 94.2,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.94,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 94.2, unit: '%' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:12', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 11:40', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 11:41', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0044',
    paperId: 'SP-006',
    sectionId: 's3',
    quote: 'High-pressure homogenisation at 1,200 bar reached 88.6 % disruption in a single pass',
    field: 'disruption_efficiency',
    value: 88.6,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.89,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 09:12', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0045',
    paperId: 'SP-006',
    sectionId: 's3',
    quote: 'three homogeniser passes raised disruption to 97.1 %',
    field: 'disruption_efficiency',
    value: 97.1,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.86,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 09:12', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 08:55', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0046',
    paperId: 'SP-006',
    sectionId: 's2',
    quote: 'the centrifuge recovered 96.4 % of the culture biomass',
    field: 'harvest_recovery',
    value: 96.4,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 96.4, unit: '%' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:13', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 11:44', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 11:44', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0047',
    paperId: 'SP-006',
    sectionId: 's2',
    quote: 'an alternative tangential-flow membrane harvest returned 91.8 % of the biomass',
    field: 'harvest_recovery',
    value: 91.8,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.81,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 09:13', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0048',
    paperId: 'SP-006',
    sectionId: 's3',
    quote: 'Soluble protein in the bead-milled lysate corresponded to 41.3 % DW by the Lowry assay',
    field: 'protein_content',
    value: 41.3,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.77,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'Lowry',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 09:14', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0049',
    paperId: 'SP-006',
    sectionId: 's2',
    quote: 'The grinding chamber jacket was held at 12 °C throughout milling',
    field: 'temperature',
    value: 12,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.72,
    status: 'rejected',
    organism: 'cw15',
    extractorRun: 'v0.4',
    rejectReason: 'not a culture temperature — the span describes the mill jacket coolant',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-13 16:02', who: 'phycoextract v0.4', action: 'extracted' },
      {
        at: '2026-07-15 11:47',
        who: 'S. Creighton',
        action: 'rejected — not a culture temperature — the span describes the mill jacket coolant',
      },
    ],
  },
  {
    id: 'ex-0050',
    paperId: 'SP-006',
    sectionId: 's2',
    quote: 'harvested at a dry cell weight of 2.6 g L⁻¹',
    field: 'final_biomass_density',
    value: 2.6,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 09:14', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 09:02', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0051',
    paperId: 'SP-006',
    sectionId: 's3',
    quote: 'Bath sonication, included as a laboratory reference, lysed only 61.5 % of cells',
    field: 'disruption_efficiency',
    value: 61.5,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 61.5, unit: '%' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-17 10:20',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-007
  {
    id: 'ex-0052',
    paperId: 'SP-007',
    sectionId: 's3',
    quote: 'Mean volumetric productivity over the linear growth phase was 0.048 g L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 0.048,
    unit: 'g L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.048, unit: 'g L⁻¹ h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:31', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 13:05', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 13:06', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0053',
    paperId: 'SP-007',
    sectionId: 's3',
    quote: 'The flat-panel array reached a final biomass density of 3.8 g L⁻¹ on day 9',
    field: 'final_biomass_density',
    value: 3.8,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:31', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 13:08', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0054',
    paperId: 'SP-007',
    sectionId: 's3',
    quote: 'the bubble columns plateaued at 2.1 g L⁻¹',
    field: 'final_biomass_density',
    value: 2.1,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.84,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 10:32', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0055',
    paperId: 'SP-007',
    sectionId: 's2',
    quote: 'an incident photon flux density of 420 µmol m⁻² s⁻¹',
    field: 'light_intensity',
    value: 420,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.91,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 10:33', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 09:20', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0056',
    paperId: 'SP-007',
    sectionId: 's2',
    quote: 'The 2 L bubble columns received 180 µmol m⁻² s⁻¹ at the vessel surface',
    field: 'light_intensity',
    value: 180,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.83,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 10:33', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0057',
    paperId: 'SP-007',
    sectionId: 's2',
    quote: 'Sparge gas was blended to 2.5 % v/v CO2',
    field: 'co2_enrichment',
    value: 2.5,
    unit: '% v/v',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 2.5, unit: '% v/v' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:34', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 13:12', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 13:12', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0058',
    paperId: 'SP-007',
    sectionId: 's2',
    quote: 'Culture temperature was maintained at 25.0 °C by a jacketed water loop',
    field: 'ph_setpoint',
    value: 7,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.62,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.3',
    audit: [{ at: '2026-07-11 14:48', who: 'phycoextract v0.3', action: 'extracted' }],
  },
  {
    id: 'ex-0059',
    paperId: 'SP-007',
    sectionId: 's3',
    quote: 'Panel surface temperature never exceeded the 25.0 °C set point',
    field: 'temperature',
    value: 25,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.79,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 10:35', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0060',
    paperId: 'SP-007',
    sectionId: 's4',
    quote: 'Productivities as high as 0.075 g L⁻¹ h⁻¹ have been claimed for outdoor tubular systems',
    field: 'volumetric_productivity',
    value: 0.075,
    unit: 'g L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.68,
    status: 'rejected',
    organism: 'cw15',
    extractorRun: 'v0.4',
    rejectReason: 'literature comparison — the value is not measured in this study',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-13 16:20', who: 'phycoextract v0.4', action: 'extracted' },
      {
        at: '2026-07-16 09:31',
        who: 'H. Ndlovu',
        action: 'rejected — literature comparison — the value is not measured in this study',
      },
    ],
  },
  {
    id: 'ex-0061',
    paperId: 'SP-007',
    sectionId: 's2',
    quote: 'the bubble columns were sparged with air enriched to 1.0 % v/v CO2',
    field: 'co2_enrichment',
    value: 1,
    unit: '% v/v',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 1, unit: '% v/v' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-17 10:26',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-008
  {
    id: 'ex-0062',
    paperId: 'SP-008',
    sectionId: 's3',
    quote: 'Nitrogen-replete cw15 contained 38.4 % DW protein by the Lowry assay',
    field: 'protein_content',
    value: 38.4,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.96,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Lowry',
    gold: { value: 38.4, unit: '% DW' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 11:05', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 14:10', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 14:10', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0063',
    paperId: 'SP-008',
    sectionId: 's3',
    quote: 'the same biomass returned 46.1 % DW by Kjeldahl digestion',
    field: 'protein_content',
    value: 46.1,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Kjeldahl',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 11:05', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 14:12', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0064',
    paperId: 'SP-008',
    sectionId: 's3',
    quote: 'cc1690 was consistently richer, at 42.7 % DW by Lowry',
    field: 'protein_content',
    value: 42.7,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'cc1690',
    componentTag: 'Lowry',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 11:06', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 10:02', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0065',
    paperId: 'SP-008',
    sectionId: 's3',
    quote: 'and 49.5 % DW by Kjeldahl on the same freeze-dried powder',
    field: 'protein_content',
    value: 49.5,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.87,
    status: 'unverified',
    organism: 'cc1690',
    componentTag: 'Kjeldahl',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 11:06', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0066',
    paperId: 'SP-008',
    sectionId: 's3',
    quote: 'the Lowry estimate for cw15 fell to 21.6 % DW',
    field: 'protein_content',
    value: 21.6,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.85,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'Lowry',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 11:07', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0067',
    paperId: 'SP-008',
    sectionId: 's2',
    quote: 'cc1690 cultures reached 1.9 g L⁻¹ dry cell weight at the point of sampling',
    field: 'final_biomass_density',
    value: 1.9,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.8,
    status: 'verified',
    organism: 'cc1690',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 11:07', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 10:05', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0068',
    paperId: 'SP-008',
    sectionId: 's2',
    quote: 'a nitrogen-to-protein factor of 6.25 was applied to all Kjeldahl estimates',
    field: 'protein_content',
    value: 62.5,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.58,
    status: 'rejected',
    organism: 'cw15',
    componentTag: 'Kjeldahl',
    extractorRun: 'v0.3',
    rejectReason: 'span reports a nitrogen-to-protein conversion factor, not a protein content',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-11 15:10', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-07-15 14:20',
        who: 'S. Creighton',
        action: 'rejected — span reports a nitrogen-to-protein conversion factor, not a protein content',
      },
    ],
  },
  {
    id: 'ex-0069',
    paperId: 'SP-008',
    sectionId: 's3',
    quote: 'Mid-exponential cw15 biomass contained 31.2 % DW protein by Lowry',
    field: 'protein_content',
    value: 31.2,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Lowry',
    gold: { value: 31.2, unit: '% DW' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-17 10:33',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-009
  {
    id: 'ex-0070',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'Mixotrophic batch cultures grew at 0.094 h⁻¹ during the first 36 h',
    field: 'growth_rate_mu',
    value: 0.094,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.97,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.094, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 12:02', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 15:01', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 15:01', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0071',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'photoautotrophic controls grew at 0.038 h⁻¹ under the same illumination',
    field: 'growth_rate_mu',
    value: 0.038,
    unit: 'd⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.66,
    status: 'unverified',
    organism: 'cw15',
    gold: { value: 0.038, unit: 'h⁻¹' },
    extractorRun: 'v0.4',
    audit: [
      { at: '2026-07-13 17:04', who: 'phycoextract v0.4', action: 'extracted' },
      { at: '2026-07-14 08:11', who: 'unit linter', action: 'flagged — unit family disagrees with source span' },
    ],
  },
  {
    id: 'ex-0072',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'Biomass yield on acetate over the feed phase was 0.41 g g⁻¹',
    field: 'yield_biomass_substrate',
    value: 0.41,
    unit: 'g g⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.94,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 12:03', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 15:04', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0073',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'the uncontrolled batch reference returned only 0.33 g g⁻¹',
    field: 'yield_biomass_substrate',
    value: 0.33,
    unit: 'g g⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.88,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 12:03', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0074',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'The fed-batch process finished at 8.6 g L⁻¹ dry cell weight after 118 h',
    field: 'final_biomass_density',
    value: 8.6,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 12:04', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 15:07', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0075',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'Protein-specific productivity averaged 14.7 mg g⁻¹ h⁻¹ across the feed phase',
    field: 'specific_productivity',
    value: 14.7,
    unit: 'mg g⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.89,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 12:04', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:12', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0076',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'this corresponds to a volumetric productivity of 0.11 g L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 0.11,
    unit: 'g L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.91,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 12:05', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:14', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0077',
    paperId: 'SP-009',
    sectionId: 's2',
    quote: 'The feed reservoir contained sodium acetate at 30.0 g L⁻¹',
    field: 'medium_component_conc',
    value: 30,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.86,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'sodium acetate',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 12:05', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0078',
    paperId: 'SP-009',
    sectionId: 's4',
    quote: 'A fed-batch that reaches 8.6 g L⁻¹ without any pigment penalty',
    field: 'final_biomass_density',
    value: 8.6,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.74,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4',
    audit: [
      { at: '2026-07-13 17:09', who: 'phycoextract v0.4', action: 'extracted' },
      { at: '2026-07-14 08:14', who: 'dedupe check', action: 'flagged as possible duplicate of ex-0074' },
    ],
  },
  {
    id: 'ex-0079',
    paperId: 'SP-009',
    sectionId: 's3',
    quote: 'the observed doubling time of 7.4 h',
    field: 'doubling_time',
    value: 7.4,
    unit: 'h',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 7.4, unit: 'h' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-17 10:41',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-010
  {
    id: 'ex-0080',
    paperId: 'SP-010',
    sectionId: 's3',
    quote: 'For cw15 the OD750-to-DCW factor was 0.42 g L⁻¹ OD⁻¹ over the linear range',
    field: 'od_dcw_factor',
    value: 0.42,
    unit: 'g L⁻¹ OD⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.98,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.42, unit: 'g L⁻¹ OD⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 13:20', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 16:02', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 16:02', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0081',
    paperId: 'SP-010',
    sectionId: 's3',
    quote: 'cc1690 required a higher factor of 0.47 g L⁻¹ OD⁻¹ over the same optical range',
    field: 'od_dcw_factor',
    value: 0.47,
    unit: 'g L⁻¹ OD⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'cc1690',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 13:21', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 12:04', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0082',
    paperId: 'SP-010',
    sectionId: 's3',
    quote: 'At 680 nm the same biomass gave 0.31 g L⁻¹ OD⁻¹',
    field: 'od_dcw_factor',
    value: 0.31,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    organism: 'cw15',
    gold: { value: 0.31, unit: 'g L⁻¹ OD⁻¹' },
    extractorRun: 'v0.4',
    audit: [
      { at: '2026-07-13 18:02', who: 'phycoextract v0.4', action: 'extracted' },
      { at: '2026-07-14 08:19', who: 'unit linter', action: 'flagged — OD basis dropped from unit string' },
    ],
  },
  {
    id: 'ex-0083',
    paperId: 'SP-010',
    sectionId: 's4',
    quote: 'The cw15 factor of 0.42 g L⁻¹ OD⁻¹ should not be transferred between strains',
    field: 'od_dcw_factor',
    value: 0.42,
    unit: 'g L⁻¹ OD⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.61,
    status: 'rejected',
    organism: 'cc1690',
    extractorRun: 'v0.3',
    rejectReason: 'organism mis-attributed — the span states the factor is specific to cw15',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-11 16:31', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-07-15 16:09',
        who: 'S. Creighton',
        action: 'rejected — organism mis-attributed — the span states the factor is specific to cw15',
      },
    ],
  },
  {
    id: 'ex-0084',
    paperId: 'SP-010',
    sectionId: 's2',
    quote: 'Maintenance cultures were held under continuous illumination at 90 µmol m⁻² s⁻¹',
    field: 'light_intensity',
    value: 90,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.87,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-14 13:22', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 12:08', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0085',
    paperId: 'SP-010',
    sectionId: 's2',
    quote: 'the highest calibration standard, 1.2 g L⁻¹',
    field: 'final_biomass_density',
    value: 1.2,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.64,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 13:23', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0086',
    paperId: 'SP-010',
    sectionId: 's3',
    quote: 'Stationary-phase cw15 cells required 0.55 g L⁻¹ OD⁻¹',
    field: 'od_dcw_factor',
    value: 0.55,
    unit: 'g L⁻¹ OD⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.55, unit: 'g L⁻¹ OD⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-17 10:52',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-011
  {
    id: 'ex-0087',
    paperId: 'SP-011',
    sectionId: 's2',
    quote: 'The harmonised baseline assumes a biomass yield on acetate of 0.45 g g⁻¹',
    field: 'yield_biomass_substrate',
    value: 0.45,
    unit: 'g g⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.45, unit: 'g g⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 14:40', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-15 17:05', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-15 17:05', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0088',
    paperId: 'SP-011',
    sectionId: 's3',
    quote: 'a photobioreactor array delivering 4.8 g L⁻¹ at harvest',
    field: 'final_biomass_density',
    value: 4.8,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.82,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 14:41', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0089',
    paperId: 'SP-011',
    sectionId: 's3',
    quote: 'disc-stack centrifugation is credited with 92.0 % harvest recovery in the baseline',
    field: 'harvest_recovery',
    value: 92,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0.88,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 14:41', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0090',
    paperId: 'SP-011',
    sectionId: 's3',
    quote: 'Settling followed by dissolved-air flotation recovers 78.5 % of Arthrospira platensis biomass',
    field: 'harvest_recovery',
    value: 78.5,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'aplat',
    gold: { value: 78.5, unit: '%' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-17 11:03',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },
];
