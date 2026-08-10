// openFerment Sim — corpus set A (SP-001 … SP-005, ex-0001 … ex-0042).
//
// SYNTHETIC CONTENT. Every author name, journal title, and measured value in
// this file is invented for the working simulation. Nothing here is attributable
// to a real researcher or a real publication (BUILD-SPEC §20).
//
// Set A covers Chlamydomonas reinhardtii cw15 (with one cc1690 comparison):
// mixotrophic kinetics on acetate, TAP medium variants, photoautotrophic vs
// mixotrophic culture, nitrogen limitation and protein content, and the photon
// flux response of flask culture.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_A: Paper[] = [
  {
    id: 'SP-001',
    title:
      'Acetate-limited mixotrophic growth kinetics of Chlamydomonas reinhardtii cw15 in shaken flask culture',
    authors: [
      'Ilse Vandergraaf',
      'Kwame Osei-Bonsu',
      'Mariko Nakagawa',
      'Tobias Ferreyra',
      'Halima Bensalem',
    ],
    year: 2019,
    venue: 'Journal of Applied Phycobiotechnology',
    organisms: ['cw15'],
    topics: ['mixotrophic growth', 'acetate uptake', 'growth kinetics'],
    abstract:
      'Reported specific growth rates for Chlamydomonas reinhardtii cw15 in Tris-acetate-phosphate medium span nearly a factor of three, and the published record rarely contains enough methodological detail to say why. We measured the mixotrophic growth kinetics of cw15 on acetate under a single, fully specified shaken-flask configuration, reporting every quantity in the units in which it was measured. Exponential growth proceeded at 0.118 per hour, giving a doubling time of 5.9 hours, and continued until acetate fell below the detection limit of the chromatographic assay. The culture reached 1.62 grams of dry cell weight per litre at 54 hours, with a biomass yield on acetate of 0.42 grams per gram. Growth ceased abruptly rather than tapering, identifying acetate rather than light as the terminal limitation. Culture pH rose from 7.0 to 8.3 over the batch, which we identify as the principal weakness of the configuration for extended culture.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text: `Chlamydomonas reinhardtii occupies an unusual position among laboratory phototrophs. It grows photoautotrophically on dissolved inorganic carbon, heterotrophically on acetate in darkness, and mixotrophically when light and acetate are supplied together. The cell-wall-deficient mutant cw15 is favoured for bioprocess work because the absent glycoprotein wall lowers the specific energy required for cell disruption and simplifies transformation, at the cost of markedly increased shear sensitivity.

Despite the volume of physiological work on this strain, reported specific growth rates in Tris-acetate-phosphate medium span nearly a factor of three, and the reasons are rarely resolvable from the published record. Rates are quoted variously per hour and per day. Biomass is reported as optical density, as cell number, or as dry weight, often without a stated conversion between them. The illumination geometry of a shaken flask is almost never specified in enough detail to reproduce, even though the difference between lateral and basal illumination of a 500 mL flask is large enough to account for much of the observed spread on its own.

The ambiguity matters because the specific growth rate is the parameter that propagates furthest into process design. Seed-train length, the number of expansion stages, and the achievable volumetric productivity of a downstream photobioreactor all follow from it. A rate that is uncertain by a factor of two produces a seed schedule that is uncertain by more than a day, and a seed schedule that is uncertain by more than a day cannot be costed.

This study characterises the mixotrophic growth of cw15 on acetate under one fully specified flask configuration. We report the exponential phase, the transition to acetate limitation, and the biomass yield on acetate, and we relate the observed rate to the oxygen transfer and illumination conditions that produced it. Our intent is to provide a reference point of sufficient methodological completeness that any discrepancy between this rate and another can be attributed to a stated cause rather than to unrecorded practice.`,
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text: `Chlamydomonas reinhardtii cw15 was maintained on Tris-acetate-phosphate agar slants at 22 °C under continuous dim illumination and subcultured every three weeks. Liquid precultures were raised in 100 mL of the same medium in 250 mL Erlenmeyer flasks and harvested in mid-exponential phase for inoculation; stationary-phase inoculum was never used.

Tris-acetate-phosphate medium was prepared to the standard formulation. Each litre contained 2.42 g L⁻¹ Tris base, 0.375 g L⁻¹ ammonium chloride, 0.100 g L⁻¹ magnesium sulfate heptahydrate, 0.050 g L⁻¹ calcium chloride dihydrate, and phosphate delivered from a concentrated stock to a final potassium phosphate concentration of 1.61 g L⁻¹. Glacial acetic acid was added to 1.05 g L⁻¹, which set the initial pH to 7.0 without further adjustment. Trace elements were supplied as a chelated metal solution at 1 mL L⁻¹. Media were autoclaved at 121 °C for 20 min and cooled to room temperature before inoculation.

Growth experiments were performed in 500 mL baffled Erlenmeyer flasks containing 150 mL of medium and closed with silicone foam plugs. Cultures were incubated at 25 °C on an orbital shaker at 130 rpm with a 25 mm orbit. Continuous illumination was supplied from below by a cool-white light-emitting diode panel delivering 60 µmol m⁻² s⁻¹ of photosynthetically active radiation at the flask base, measured with a spherical quantum sensor immersed in water at the working liquid depth. Flasks were inoculated to an initial optical density at 750 nm of 0.05.

Samples of 5 mL were withdrawn every 3 h through the first 36 h and every 6 h thereafter. Optical density was read at 750 nm against a medium blank, with dilution into the linear range where required. Dry cell weight was determined in triplicate by filtering 10 mL of culture onto pre-dried glass fibre filters, washing twice with deionised water, and drying at 105 °C to constant mass. Acetate in the 0.2 µm filtrate was quantified by high-performance liquid chromatography with refractive index detection. The specific growth rate was obtained by unweighted linear regression of the natural logarithm of dry cell weight against time, over the interval in which the residuals showed no systematic trend.`,
      },
      {
        id: 's3',
        heading: 'Results',
        text: `Cultures entered exponential growth after a lag of approximately 4 h and maintained an unrestricted rate until acetate fell below roughly 0.2 g L⁻¹. Regression of the natural logarithm of dry cell weight against time over the interval from 6 h to 30 h gave a specific growth rate of 0.118 h⁻¹, with a 95 per cent confidence interval of 0.112 to 0.124, corresponding to a doubling time of 5.9 h. Residuals were unstructured across this window, and the same regression performed on optical density rather than on dry weight returned a rate indistinguishable within the confidence interval.

Growth ceased abruptly rather than tapering, which is the signature of a carbon-limited rather than a light-limited culture at this cell density. The final biomass density reached 1.62 g L⁻¹ at 54 h, at which point acetate was below the detection limit of the chromatographic method. No further increase in dry weight was observed over the subsequent 18 h, and the culture retained full green pigmentation, indicating that nitrogen remained in excess at harvest.

Acetate consumption tracked biomass formation closely. Across the exponential phase the biomass yield on acetate was 0.42 g g⁻¹, calculated as the slope of dry weight formed against acetate consumed over the interval in which both were measured with better than 5 per cent relative precision. The yield showed no drift with culture age until the final 6 h before acetate exhaustion, when it declined as maintenance demand became a larger fraction of the total carbon flux.

Culture pH rose from 7.0 to 8.3 over the course of the batch, consistent with the net proton consumption that accompanies uptake of the acetate anion and with the limited buffering capacity of Tris at the upper end of its range. Cell counts and dry weight remained proportional throughout, with a mean conversion of 0.31 g L⁻¹ per unit optical density at 750 nm, and we saw none of the cell enlargement that accompanies nutrient limitation in this strain.`,
      },
      {
        id: 's4',
        heading: 'Discussion',
        text: `The specific growth rate reported here sits in the upper part of the range recorded for cw15 in Tris-acetate-phosphate medium, and the methodological detail allows that position to be explained rather than merely noted. Three choices raise the rate relative to more commonly used configurations. Baffled flasks with a 150 mL fill in a 500 mL vessel sustain the oxygen transfer that acetate respiration requires. Illumination from below rather than laterally removes the self-shading gradient that develops across a flask wall as density rises. A preculture harvested in mid-exponential phase shortens the lag and avoids the storage-carbon burden carried by a stationary inoculum.

The biomass yield on acetate is consistent with a mixotrophic carbon economy in which photosynthetically fixed carbon supplements the acetate skeleton rather than replacing it. A purely heterotrophic culture on acetate would be expected to yield below 0.35 g g⁻¹ once maintenance is accounted for, and a purely photoautotrophic culture consumes no acetate at all. The intermediate value observed here, together with the abrupt cessation of growth at acetate exhaustion, indicates that acetate remained the limiting carbon source throughout while light contributed reducing power and adenosine triphosphate.

The pH excursion to 8.3 is the principal weakness of the configuration. Above pH 8 the fraction of inorganic carbon present as dissolved carbon dioxide falls sharply, and the photosynthetic contribution to mixotrophic growth becomes progressively harder to sustain. For cultures intended to run beyond acetate exhaustion, either a higher Tris concentration or an external pH control loop is warranted, and we take up the first of those options in companion work on medium variants.

We recommend that the rate reported here be treated as an upper reference for shaken-flask mixotrophic culture of cw15, applicable only where oxygen transfer and illumination are demonstrably not limiting. Extrapolation to bubble-column or stirred-tank geometry requires an explicit accounting of both.`,
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-002',
    title:
      'Buffer and nitrogen variants of Tris-acetate-phosphate medium for higher-density flask culture of Chlamydomonas reinhardtii cw15',
    authors: [
      'Sofia Almeida Rocha',
      'Deniz Aydinli',
      'Peter Okonkwo',
      'Yun-Seo Baek',
    ],
    year: 2021,
    venue: 'Algal Media and Bioprocess Reports',
    organisms: ['cw15'],
    topics: ['media optimization', 'tap medium', 'buffer capacity'],
    abstract:
      'Tris-acetate-phosphate medium was formalised for maintenance and genetic work, not for biomass production, and two of its properties limit the density a flask culture can reach. Buffer capacity is exhausted within a single batch because acetate uptake consumes protons, and the standard ammonium charge supports well under two grams of dry biomass per litre. We compared standard medium against a doubled-buffer variant and a doubled-nitrogen variant in Chlamydomonas reinhardtii cw15 under matched illumination. Doubling Tris and acetate together raised the specific growth rate only marginally, from 0.104 to 0.109 per hour, but held terminal pH below 7.6 instead of allowing an excursion past 8.3. Doubling ammonium chloride left the growth rate unchanged while raising the final biomass density to 2.35 grams per litre. We conclude that buffer and nitrogen limit different things, that neither substitutes for the other, and that both modifications should be reported explicitly rather than folded into the phrase modified medium.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text: `Tris-acetate-phosphate medium is the default growth medium for laboratory Chlamydomonas culture, and its composition has changed little since it was formalised. It was designed for strain maintenance and genetic work rather than for biomass production, and two of its properties become limiting as soon as a culture is asked to reach a density of any process interest.

The first is buffer capacity. Tris has a useful buffering range that the culture exits within a single batch, because uptake of the acetate anion is a net proton-consuming process and the pH therefore drifts upward rather than down. Once the culture passes pH 8, the equilibrium fraction of inorganic carbon present as dissolved carbon dioxide collapses, and the photosynthetic half of mixotrophic growth becomes progressively harder to sustain at exactly the point in the batch where cell density makes light delivery hardest.

The second is nitrogen supply. The standard ammonium charge supports a limited quantity of protein-rich biomass before nitrogen becomes the terminal constraint, and that ceiling sits well below what the carbon charge could support. Cultures grown to nitrogen exhaustion do not simply stop; they reallocate carbon into starch and neutral lipid and their protein fraction falls, so a nitrogen-limited batch changes composition as well as quantity.

Practitioners routinely modify the recipe to work around both problems, but the modifications are recorded inconsistently. Papers describe modified Tris-acetate-phosphate medium without stating which component moved, or report a doubled recipe without saying whether acetate was doubled alongside the Tris that neutralises it. The result is a literature in which two nominally identical media differ by a factor of two in a component that determines the answer.

This study compares standard medium against two explicitly specified variants under otherwise matched conditions, and reports the full composition of each. We measure the specific growth rate, the terminal pH, and the final biomass density, and we separate the effects of buffer capacity from those of nitrogen supply.`,
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text: `Chlamydomonas reinhardtii cw15 was recovered from a cryopreserved working bank and passaged twice in liquid medium before use. All treatments were inoculated from a single common preculture harvested in mid-exponential phase, so that inoculum history could not contribute to the differences between them.

Standard Tris-acetate-phosphate medium contained 2.42 g L⁻¹ Tris base, 0.375 g L⁻¹ ammonium chloride, 0.100 g L⁻¹ magnesium sulfate heptahydrate, 0.050 g L⁻¹ calcium chloride dihydrate, potassium phosphate to 1.61 g L⁻¹, and glacial acetic acid to 1.05 g L⁻¹, giving an initial pH of 7.0. The doubled-buffer variant, designated TAP-2T, contained 4.84 g L⁻¹ Tris base and glacial acetic acid to 2.10 g L⁻¹, with all remaining components at standard concentration; acetate was doubled alongside the Tris so that the initial pH of the variant matched the standard medium rather than drifting alkaline at the outset. The doubled-nitrogen variant, designated TAP-2N, raised the nitrogen source to 0.750 g L⁻¹ ammonium chloride with all other components at standard concentration. Trace elements were identical across all three media.

Cultures were grown in 500 mL baffled Erlenmeyer flasks with a 150 mL working volume. Flasks were incubated at 24 °C under continuous illumination at 80 µmol m⁻² s⁻¹ supplied from a warm-white light-emitting diode array beneath the shaker platform, and agitated at 140 rpm. Each medium was run in quadruplicate and the entire experiment was repeated on two separate occasions with independently prepared media.

Optical density at 750 nm was recorded every 4 h. Dry cell weight was measured gravimetrically on filtered 10 mL samples dried to constant mass at 105 °C. Culture pH was measured off-line in the withdrawn sample rather than in the flask, to avoid the carbon dioxide equilibration artefact that accompanies opening a shaken vessel. Specific growth rates were fitted over the interval from 8 h to 32 h, which lay within the exponential phase for every treatment. Ammonium was determined colorimetrically and acetate by high-performance liquid chromatography.`,
      },
      {
        id: 's3',
        heading: 'Results',
        text: `In standard medium the cultures grew with a specific growth rate of 0.104 h⁻¹ and reached a final biomass density of 1.48 g L⁻¹ at 60 h. Ammonium was exhausted at approximately 52 h, before acetate, so the standard formulation terminated on nitrogen rather than on carbon under these conditions. Terminal pH was 8.4.

Doubling the buffer changed the pH trajectory decisively and the growth rate only marginally. The high-buffer variant grew at 0.109 h⁻¹, a difference of approximately 5 per cent that was reproducible across both experimental occasions but small relative to the pH effect. Terminal pH in TAP-2T was 7.6, compared with 8.4 in standard medium, and the culture remained within the working range of the buffer for the whole of the exponential phase. Final biomass density in TAP-2T was 1.55 g L⁻¹, statistically indistinguishable from standard medium, confirming that the additional acetate was not consumed once nitrogen ran out.

Doubling the nitrogen source changed the ceiling without changing the rate. TAP-2N grew at 0.105 h⁻¹, indistinguishable from standard medium, but continued growing for a further 14 h and reached a final biomass density of 2.35 g L⁻¹. Acetate was exhausted at 71 h in this treatment, so TAP-2N terminated on carbon rather than nitrogen, which is the intended behaviour for a medium used to produce biomass. Terminal pH in TAP-2N was 8.7, higher than the standard medium because more acetate had been consumed against the same quantity of buffer.

The three media therefore failed for three different reasons, and the failure mode is diagnostic. A culture that stops with acetate remaining is nitrogen-limited. A culture that stops with ammonium remaining is carbon-limited. A culture that stops with both remaining, which we observed only in a preliminary trial at higher cell density, is light-limited and neither modification will help it.`,
      },
      {
        id: 's4',
        heading: 'Discussion',
        text: `Buffer and nitrogen limit different things, and the practical consequence is that neither modification substitutes for the other. Doubling Tris does not raise the biomass ceiling because the ceiling was never set by pH under these conditions; it protects the pH trajectory, which matters for the photosynthetic contribution to mixotrophic growth and for any downstream step whose recovery depends on the surface charge of the cell. Doubling ammonium raises the ceiling by more than half but leaves the culture spending its final hours above pH 8.5, where dissolved carbon dioxide is scarce.

The obvious inference is that a medium intended for biomass production should carry both modifications, and our preliminary combined formulation supports that, but we report it only as an observation because it was not run with the replication of the three principal treatments. The doubling of acetate alongside Tris in the high-buffer variant is not optional. Tris and acetic acid are titrated against one another in this recipe, and raising Tris alone yields a medium with a higher starting pH and a lower carbon charge, which is a different experiment from the one intended.

We would draw one methodological conclusion beyond the medium itself. Reporting a growth rate without the terminal pH and without the identity of the exhausted nutrient leaves the reader unable to tell which of these three regimes produced the number. In the present data the specific growth rates of the three media differ by less than 5 per cent while their final biomass densities differ by 59 per cent, so a study reporting only the rate would have concluded, incorrectly, that the medium made no difference.`,
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-003',
    title:
      'Photoautotrophic and mixotrophic culture of Chlamydomonas reinhardtii compared under matched illumination: strains cw15 and cc1690',
    authors: [
      'Anais Berthelot',
      'Rahul Vaidyanathan',
      'Ingrid Sorensen',
      'Chukwuemeka Adeyemi',
      'Lucia Ferrante',
    ],
    year: 2020,
    venue: 'International Review of Phototrophic Bioprocessing',
    organisms: ['cw15', 'cc1690'],
    topics: ['photoautotrophic growth', 'mixotrophic growth', 'strain comparison'],
    abstract:
      'Comparisons between photoautotrophic and mixotrophic culture of Chlamydomonas are usually confounded by illumination that differs between the two conditions, because the denser mixotrophic culture attenuates more light. We compared both trophic modes for the cell-wall-deficient strain cw15 and the walled strain cc1690 in flat-panel vessels of identical optical path, holding incident photon flux density constant at 150 micromoles per square metre per second. Mixotrophic cw15 grew at 0.132 per hour against a photoautotrophic rate of 0.061 per hour, a factor of 2.2. The walled strain was slower in both modes. Mixotrophic cultures reached 1.95 grams per litre while photoautotrophic cultures plateaued at 0.74 grams per litre, and the protein fraction of mixotrophic biomass was lower than that of photoautotrophic biomass at the same harvest point. We argue that the rate advantage of mixotrophy is real but is purchased with an organic carbon input that a photoautotrophic process does not require.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text: `The decision between photoautotrophic and mixotrophic culture is the first branch point in the design of any Chlamydomonas process, and it is usually made on the basis of growth rate alone. Mixotrophic culture on acetate is faster, and the literature says so consistently. What the literature says much less consistently is how much faster, under what illumination, and at what cost in organic carbon.

Most published comparisons are confounded in the same way. The mixotrophic culture reaches a higher cell density, a denser culture attenuates more of the incident light, and the two conditions therefore experience different average photon flux densities inside the vessel even when the lamp setting is identical. Comparisons made in Erlenmeyer flasks compound the problem, because the optical path through a swirling flask is neither constant nor easily stated. The measured advantage of mixotrophy in such a comparison is partly an artefact of the comparison.

A second confound is strain. The cell-wall-deficient mutant cw15 is the workhorse of bioprocess studies because it disrupts easily, while walled strains such as cc1690 are more common in physiological work. The two are not interchangeable. The absent wall changes shear tolerance, settling behaviour, and the energetic burden of wall synthesis, and any of these could plausibly shift the balance between trophic modes.

We therefore compared both trophic modes in both strains using flat-panel vessels of identical optical path, with incident photon flux density held constant and measured at the vessel surface rather than inferred from a lamp specification. We report growth rate, final biomass density, and protein content for all four combinations, and we consider what the rate advantage of mixotrophy actually costs when the acetate input is accounted for rather than assumed free.`,
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text: `Chlamydomonas reinhardtii cw15 and cc1690 were maintained separately and never handled on the same day, to eliminate cross-contamination between a walled and a wall-deficient strain that would be difficult to detect by microscopy alone. Both strains were passaged three times in the medium of their respective treatment before the experiment began, so that no culture carried a metabolic history from the other trophic mode.

Mixotrophic cultures were grown in standard Tris-acetate-phosphate medium. Photoautotrophic cultures were grown in the same medium with acetic acid omitted and the Tris charge titrated to pH 7.2 with hydrochloric acid, so that buffer identity and concentration were preserved while organic carbon was removed. Photoautotrophic vessels were sparged with air enriched to 2 per cent carbon dioxide by volume at 0.05 vvm; mixotrophic vessels received the same sparge, so that inorganic carbon supply was not a variable between the trophic modes.

All cultures were grown in flat-panel vessels of 400 mL working volume with a 20 mm optical path, illuminated on one face by a white light-emitting diode panel providing a photon flux density of 150 µmol m⁻² s⁻¹ at the vessel surface. Incident flux was verified with a planar quantum sensor at nine positions across the illuminated face before each run, and treatments were rotated between panel positions between replicates. Vessels were held at 25 °C in a temperature-controlled cabinet and mixed by the sparge alone.

Dry cell weight was determined gravimetrically in triplicate. Specific growth rates were fitted over the exponential interval identified separately for each treatment, since the photoautotrophic cultures remained exponential for considerably longer than the mixotrophic ones. Total protein was determined on washed, freeze-dried biomass by the Lowry method against a bovine serum albumin standard curve, with results expressed as a percentage of dry weight. Chlorophyll was extracted in methanol and quantified spectrophotometrically.`,
      },
      {
        id: 's3',
        heading: 'Results',
        text: `The trophic mode dominated the growth rate in both strains, and the strain difference was consistent but smaller. Under mixotrophic conditions cw15 grew at 0.132 h⁻¹ in mixotrophic culture, while the photoautotrophic rate for cw15 was 0.061 h⁻¹, a ratio of 2.2 between the two modes. The walled strain was slower in both modes: cc1690 grew at 0.097 h⁻¹ under the same mixotrophic conditions, and cc1690 reached only 0.052 h⁻¹ under photoautotrophic conditions.

Final biomass densities separated the modes more sharply than the rates did. Mixotrophic cw15 reached a final biomass density of 1.95 g L⁻¹ at 48 h, whereas photoautotrophic cultures plateaued at 0.74 g L⁻¹ and did so only after 132 h. The photoautotrophic plateau was not caused by nutrient exhaustion, since both ammonium and phosphate remained measurable at harvest; it reflects the point at which self-shading reduced the average internal photon flux below the compensation requirement of the deeper layers.

Biomass composition moved in the opposite direction to biomass quantity. In mixotrophic cw15 total protein reached 29 % DW by the Lowry method at the 48 h harvest, while photoautotrophic cw15 harvested at plateau contained 41 % DW, and the walled strain followed the same pattern with a smaller spread. The mixotrophic cultures carried a visibly larger starch complement, consistent with a carbon supply that exceeded the rate at which nitrogen could be assimilated into protein.

Chlorophyll content differed accordingly. Photoautotrophic cultures were markedly greener per unit dry weight, and the chlorophyll a to b ratio settled at 2.4 in both strains under photoautotrophic conditions against 3.1 under mixotrophy, indicating a larger relative antenna in the light-limited cultures. Acetate was fully consumed in every mixotrophic vessel by 44 h.`,
      },
      {
        id: 's4',
        heading: 'Discussion',
        text: `The rate advantage of mixotrophy in cw15 is real, survives a comparison in which incident illumination is genuinely matched, and is large enough to matter to a seed train. It is not, however, free, and the accounting rarely appears alongside the rate. Every gram of mixotrophic biomass produced in these vessels consumed acetate that had to be manufactured, shipped, sterilised, and eventually neutralised, and the pH excursion it produces has to be absorbed by buffer that is itself a cost.

The composition result cuts against the rate result and deserves more attention than it usually receives. Photoautotrophic biomass in this experiment was substantially richer in protein than mixotrophic biomass harvested from the same strain, so a process whose product is protein rather than dry mass does not gain the full factor of 2.2 that the rates suggest. Multiplying rate by protein fraction closes roughly a third of the gap, and the remainder narrows further if the acetate input is charged against the mixotrophic case.

The strain comparison is the least surprising part of the result. The walled strain grew more slowly in both modes, which is consistent with the metabolic burden of wall synthesis, but the ratio between its trophic modes was almost identical to that of the wall-deficient strain. We take this to mean that the wall affects the magnitude of growth but not the relative economics of the two carbon regimes, and that data on trophic mode can reasonably be transferred between the two strains where data on absolute rate cannot.

The principal limitation of this work is the fixed optical path. A 20 mm panel is not a production geometry, and the photoautotrophic plateau we observed is a property of that path length as much as of the organism.`,
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-004',
    title:
      'Nitrogen limitation reallocates biomass composition in Chlamydomonas reinhardtii cw15: protein, starch, and lipid trajectories',
    authors: [
      'Marisol Quispe Alvarado',
      'Jonas Wehrli',
      'Fatoumata Diallo',
      'Hiroshi Ozaki',
    ],
    year: 2022,
    venue: 'Journal of Microalgal Composition Science',
    organisms: ['cw15'],
    topics: ['nitrogen limitation', 'protein content', 'biomass composition'],
    abstract:
      'Nitrogen limitation is the standard lever for inducing storage-compound accumulation in green algae, and it is applied routinely without a clear account of what it costs in protein. We followed the composition of Chlamydomonas reinhardtii cw15 through a controlled nitrogen downshift, holding temperature, illumination, and acetate supply constant so that composition changes could be attributed to nitrogen alone. Replete cultures grew at 0.112 per hour and contained 38 per cent protein by dry weight. After the downshift the residual growth rate fell to 0.038 per hour, protein passed through an intermediate value of 24 per cent by dry weight at 24 hours, and reached 17 per cent by dry weight at 48 hours. Starch accumulated first and was partially remobilised into neutral lipid after 30 hours. The protein loss is not recovered by resupplying nitrogen within the same batch, which has direct consequences for any process whose product is protein.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text: `Nitrogen limitation is the most widely used lever for pushing green algal biomass toward storage compounds. Withdraw nitrogen from a growing culture and carbon that would have become protein becomes starch instead, and after a longer interval a fraction of that starch is remobilised into neutral lipid. The manipulation is simple, robust, and effective, which is why it appears in almost every process proposal for algal lipid.

What appears far less often is a quantitative account of what the manipulation costs. Protein is not merely diluted during nitrogen limitation; it is actively degraded, since the nitrogen locked in existing protein is the only nitrogen source available to a starved cell and the photosynthetic apparatus is the largest protein pool the cell holds. A culture pushed hard toward lipid is therefore dismantling the machinery that fixes the carbon the lipid is made from, and the trajectory of that dismantling determines when the manipulation stops paying.

For processes whose product is protein rather than lipid, the same trajectory is the whole story in reverse. Algal protein for food or feed applications is valued on the protein fraction of the dry weight, and any nitrogen limitation encountered accidentally, through an inadequate ammonium charge in the medium or through an overextended batch, is a direct loss of product quality. The composition of a batch that ran a day too long is not the composition of the batch that was designed.

We therefore followed protein, starch, and neutral lipid through a controlled nitrogen downshift in cw15, with temperature, illumination, and acetate supply deliberately held constant so that no observed composition change could be attributed to anything but nitrogen. We also tested whether protein recovers when nitrogen is resupplied within the same batch, since the reversibility of the manipulation determines whether an overrun is recoverable or terminal.`,
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text: `Chlamydomonas reinhardtii cw15 was grown in standard Tris-acetate-phosphate medium to mid-exponential phase, harvested by centrifugation at 1500 g for 5 min, washed twice in nitrogen-free medium, and resuspended in the treatment medium at an optical density at 750 nm of 0.4. The gentle centrifugation is necessary for this strain: at higher relative centrifugal field the wall-deficient cells shear and the released material interferes with the subsequent protein assay.

The replete treatment used standard medium containing 0.375 g L⁻¹ ammonium chloride. In the limited treatment ammonium chloride was reduced to 0.094 g L⁻¹, one quarter of the standard charge, which exhausts within approximately 8 h of resuspension at this inoculum density and produces a defined downshift rather than a gradual taper. A third treatment received no nitrogen at all and served to confirm that the limited treatment was not simply starving from the outset. Acetate was supplied at the standard concentration in all treatments and was replenished at 24 h and 48 h from a sterile concentrate, so that carbon never became limiting.

Cultures were maintained at 25 °C in an illuminated orbital incubator at 100 µmol m⁻² s⁻¹ with continuous illumination, in 500 mL baffled flasks at a 150 mL working volume, agitated at 130 rpm. Initial pH was 7.0 in every treatment.

Samples were taken at 0, 6, 12, 24, 36, 48, and 72 h. Total protein was determined on washed, freeze-dried biomass by the Lowry method with bovine serum albumin as standard. Starch was determined enzymatically after alkaline gelatinisation, and total lipid gravimetrically after extraction into a chloroform and methanol mixture. Residual ammonium in the filtrate was measured colorimetrically at every time point. In the resupply experiment, ammonium chloride was restored to the standard concentration at 48 h and the culture followed for a further 48 h.`,
      },
      {
        id: 's3',
        heading: 'Results',
        text: `Replete cultures behaved as expected. The replete cultures grew at 0.112 h⁻¹ through the first 30 h and maintained a protein content of 38 % DW in nitrogen-replete cultures across the whole exponential phase, with no systematic trend in composition while nitrogen remained measurable in the filtrate.

Ammonium in the limited treatment fell below the detection limit at 9 h, and the culture responded within one generation. Growth did not stop, but the residual rate under nitrogen limitation was 0.038 h⁻¹, roughly a third of the replete rate, sustained by continued carbon fixation into storage compounds rather than by the balanced synthesis of new cells. All cultures were held at 25 °C throughout the shift, so none of the composition changes described below can be ascribed to a temperature effect.

Protein fell monotonically once ammonium was exhausted, passing through an intermediate value of 24 % DW at 24 h and continuing downward, so that protein had fallen to 17 % DW after 48 h of nitrogen starvation. The decline was steepest between 12 h and 30 h and flattened thereafter as the residual protein pool approached what the cell appears to defend. The nitrogen-free treatment reached a similar endpoint approximately 8 h earlier, confirming that the limited treatment was tracking nitrogen exhaustion rather than an artefact of the washing procedure.

Starch and lipid moved on different timescales. Starch rose steeply from 12 h to reach a maximum of 41 % DW at 30 h, then declined. Neutral lipid was almost unchanged for the first 30 h and then rose, reaching 22 % DW at 72 h, with the timing of the crossover suggesting partial remobilisation of starch rather than independent accumulation from newly fixed carbon.

Resupplying ammonium at 48 h restored growth within 6 h but did not restore composition within the batch. Protein at 96 h in the resupplied cultures was 26 % DW, well short of the replete value, because the recovered nitrogen was largely committed to new biomass rather than to the reconstruction of the existing cells.`,
      },
      {
        id: 's4',
        heading: 'Discussion',
        text: `The trajectory reported here has a practical shape worth stating plainly. Protein loss begins immediately on nitrogen exhaustion and is fastest in the first day, whereas lipid accumulation does not begin in earnest until the second. A process aimed at lipid must therefore accept a protein loss that is largely complete before the product it wants has started to appear, and a process aimed at protein has less margin than it might assume, since a batch that overruns by 24 h has already given up more than a third of its protein fraction.

The resupply result is the more consequential finding for process operation. Restoring nitrogen restored growth quickly but did not restore composition within the batch, because the nitrogen was allocated preferentially to new cells rather than to rebuilding the photosynthetic apparatus of the starved ones. An operator who detects nitrogen exhaustion and corrects it has not recovered the batch; they have started a second, smaller batch inside the first, and the harvested composition will be a weighted average of two populations. The correct response to an inadequate ammonium charge is to fix the medium, not to rescue the run.

We note one limitation. The downshift used here is abrupt by design, engineered to separate the effect of nitrogen from everything else, and a real batch running out of nitrogen does so gradually as the culture draws the last of it down. The gradual case will show the same endpoints but a slower and less clearly staged trajectory, and the intermediate protein values reported here should not be read as a calibration for it.

Finally, protein content by the Lowry method on this strain runs slightly high relative to nitrogen-based estimates, and comparisons with values obtained by other methods should account for that offset.`,
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-005',
    title:
      'Photon flux density response of mixotrophic Chlamydomonas reinhardtii cw15 in shaken flask culture: saturation and photoinhibition',
    authors: [
      'Amara Nwachukwu',
      'Lea Chevallier',
      'Tomas Iriarte',
      'Nadia Haddad',
      'Bjarne Lindqvist',
      'Wei-Lun Chang',
    ],
    year: 2023,
    venue: 'Photobioprocess Letters',
    organisms: ['cw15'],
    topics: ['light intensity', 'photoinhibition', 'flask culture'],
    abstract:
      'Flask illumination is the least standardised variable in laboratory algal culture and one of the largest sources of disagreement between reported growth rates. We measured the response of mixotrophic Chlamydomonas reinhardtii cw15 across five photon flux densities spanning a factor of forty-five, with incident flux measured at the liquid surface rather than inferred from a lamp specification. Growth rose steeply from the lowest treatment, saturated near the middle of the range, and declined at the highest. The maximum specific growth rate of 0.141 per hour was reached at 150 micromoles per square metre per second, was not exceeded at 400, and fell to 0.089 per hour at 900 where the cultures also bleached. Final biomass density peaked at 2.24 grams per litre. Because saturation occurs well below the illumination many laboratories default to, we argue that most reported flask cultures are on the flat part of this curve.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text: `Illumination is the least standardised variable in laboratory algal culture. Media are written down component by component, temperature is set on a dial and reported, agitation is a number in revolutions per minute, but light is routinely described as a shelf in an incubator or a lamp at a distance, and sometimes as nothing at all. Where a photon flux density is reported, it is often the manufacturer specification of the fixture rather than a measurement at the culture surface, and the two can differ by a factor of two before any account is taken of vessel geometry.

The consequence is a literature in which growth rates for the same strain in the same medium disagree without any stated reason, because the variable that differs was never recorded. For mixotrophic culture the problem is compounded by a widespread assumption that light does not much matter when acetate is present. That assumption is wrong at both ends of the range. At low flux the photosynthetic contribution to mixotrophic growth is small and the culture approaches heterotrophic behaviour. At high flux the culture is photoinhibited, and a wall-deficient strain with no protective structure outside the plasma membrane is a plausible candidate for sensitivity.

Between those ends lies a saturation point whose position determines whether raising the lamp setting is a useful intervention or an expensive one. If saturation occurs below the illumination that laboratories habitually use, then most published flask work sits on the flat part of the curve, differences in reported illumination explain nothing, and the disagreement in reported rates must come from elsewhere.

We therefore measured the growth response of mixotrophic cw15 across five photon flux densities spanning a factor of forty-five, with incident flux measured in the vessel at the working liquid depth, and we report the position of the saturation point and the onset of inhibition.`,
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text: `Chlamydomonas reinhardtii cw15 was grown in standard Tris-acetate-phosphate medium at an initial pH of 7.0 in 500 mL baffled Erlenmeyer flasks containing 150 mL of medium, agitated at 130 rpm on an orbital shaker with a 25 mm orbit and held at 25 °C. All flasks were inoculated from one common preculture to an optical density at 750 nm of 0.05.

Five illumination treatments were established: 20, 60, 150, 400, and 900 µmol m⁻² s⁻¹, and the highest treatment delivered 900 µmol m⁻² s⁻¹ measured at the liquid surface. Illumination was supplied from below by dimmable cool-white light-emitting diode panels, one panel per treatment, with the panels separated by matte black baffles to prevent cross-illumination between treatments on the same shaker. Photon flux density was measured before every run with a spherical quantum sensor immersed at the working liquid depth in a flask of sterile medium, and again at the end of each run to confirm that no panel had drifted. Flasks within a treatment were rotated between positions daily.

Because light-emitting diode panels dissipate heat, the temperature of every flask was logged continuously with a submerged probe in a sacrificial vessel per treatment, and forced air cooling was applied beneath the highest two panels so that no treatment exceeded 25.6 °C at any point. Without that cooling the highest treatment ran approximately 2 °C warmer than the lowest, which would have confounded the illumination effect entirely.

Optical density at 750 nm was recorded every 4 h and dry cell weight gravimetrically every 12 h. Specific growth rates were fitted over the interval from 8 h to 28 h. Chlorophyll was extracted into methanol and expressed per unit dry weight. The maximum quantum yield of photosystem II was measured on dark-adapted samples by pulse-amplitude-modulated fluorometry as an independent indicator of photoinhibition. Every treatment was run in triplicate on three separate occasions.`,
      },
      {
        id: 's3',
        heading: 'Results',
        text: `The growth response was saturating with a clear inhibitory arm. At the lowest treatment growth was slow but healthy: cultures at 20 µmol m⁻² s⁻¹ grew at 0.071 h⁻¹, roughly half the saturated rate, and reached the highest chlorophyll content of any treatment. Rate rose steeply through the intermediate treatments, and the maximum specific growth rate of 0.141 h⁻¹ was reached at 150 µmol m⁻² s⁻¹. Increasing incident flux beyond that point bought nothing: the 400 treatment grew at 0.138 h⁻¹, indistinguishable from the maximum within the replicate spread.

At the highest treatment the response reversed. Photoinhibited cultures grew at 0.089 h⁻¹, a reduction of 37 per cent relative to the saturated rate, and the maximum quantum yield of photosystem II in dark-adapted samples fell from 0.71 in the saturated treatment to 0.52, confirming that the rate loss was photoinhibitory rather than thermal or nutritional. The cultures were visibly pale from 16 h onward, and chlorophyll fell to 33 mg g⁻¹ at the highest photon flux against 61 mg g⁻¹ in the 20 treatment.

Final biomass density followed the same shape as the growth rate but peaked slightly later in the illumination series. The saturated treatment reached a final biomass density of 2.24 g L⁻¹ at 60 h, the 400 treatment reached 2.19 g L⁻¹, and the highest treatment reached only 1.61 g L⁻¹ despite receiving six times the photons of the saturated one. The lowest treatment reached 1.44 g L⁻¹ and required 84 h to do so.

Acetate was exhausted in every treatment, so none of the cultures terminated on carbon supply differences. Terminal pH ranged narrowly from 8.2 to 8.5 across all five treatments, and residual ammonium was below detection at harvest in the three fastest treatments only.`,
      },
      {
        id: 's4',
        heading: 'Discussion',
        text: `The saturating flux we measured sits below the illumination that many laboratories default to, which has an immediate implication for the interpretation of published flask work. A study reporting culture at 200 or 300 micromoles per square metre per second is operating on the flat part of this curve, and a study reporting 150 is at its knee. Differences in reported illumination across that band therefore explain very little of the spread in reported growth rates for this strain, and the explanation must be sought in oxygen transfer, inoculum condition, and the geometry of illumination rather than in its magnitude.

The saturating rate of 0.141 h⁻¹ was not exceeded at higher photon flux, and this is the practically useful result: raising the lamp setting above the knee costs energy and delivers nothing, while raising it far above the knee costs energy and delivers a 37 per cent penalty. For a shaken-flask seed train the correct setting is at or slightly below the knee, where the culture is fast and the panel is not being asked to push photons into a suspension that cannot use them.

The photoinhibition observed at the highest treatment deserves one caution. Our flasks were illuminated from below through a thin liquid layer at the base, which exposes the cells passing through that layer to close to the incident flux. A laterally illuminated vessel of the same nominal setting delivers a lower average flux and would be expected to show inhibition at a higher nominal value. The inhibition threshold reported here is therefore specific to basal illumination and should not be transferred to other geometries without adjustment.

We would also note that the temperature control described in the methods was not optional. In a preliminary run without forced cooling, the highest treatment ran warmer than the lowest by roughly 2 °C, and the apparent inhibition was correspondingly overstated.`,
      },
    ],
    ingest: 'complete',
  },
];

export const RECORDS_A: ExtractionRecord[] = [
  // ---------------------------------------------------------------- SP-001
  {
    id: 'ex-0001',
    paperId: 'SP-001',
    sectionId: 's3',
    quote: 'a specific growth rate of 0.118 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.118,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.96,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.118, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:12', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:40', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0002',
    paperId: 'SP-001',
    sectionId: 's3',
    quote: 'corresponding to a doubling time of 5.9 h',
    field: 'doubling_time',
    value: 5.9,
    unit: 'h',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:12', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:42', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0003',
    paperId: 'SP-001',
    sectionId: 's3',
    quote: 'The final biomass density reached 1.62 g L⁻¹ at 54 h',
    field: 'final_biomass_density',
    value: 1.62,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.91,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:13', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:45', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0004',
    paperId: 'SP-001',
    sectionId: 's2',
    quote: 'Cultures were incubated at 25 °C on an orbital shaker at 130 rpm',
    field: 'temperature',
    value: 25,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.94,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:11', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:47', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0005',
    paperId: 'SP-001',
    sectionId: 's2',
    quote: 'Each litre contained 2.42 g L⁻¹ Tris base',
    field: 'medium_component_conc',
    value: 2.42,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Tris base',
    gold: { value: 2.42, unit: 'g L⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:10', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:50', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0006',
    paperId: 'SP-001',
    sectionId: 's2',
    quote: '0.375 g L⁻¹ ammonium chloride',
    field: 'medium_component_conc',
    value: 0.375,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'ammonium chloride',
    gold: { value: 0.375, unit: 'g L⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:10', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 11:51', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0007',
    paperId: 'SP-001',
    sectionId: 's2',
    quote: 'delivering 60 µmol m⁻² s⁻¹ of photosynthetically active radiation',
    field: 'light_intensity',
    value: 60,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.83,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4',
    audit: [{ at: '2026-07-02 15:26', who: 'phycoextract v0.4', action: 'extracted' }],
  },
  {
    id: 'ex-0008',
    paperId: 'SP-001',
    sectionId: 's3',
    quote: 'the biomass yield on acetate was 0.42 g g⁻¹',
    field: 'yield_biomass_substrate',
    value: 0.42,
    unit: 'g g⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.86,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4',
    audit: [{ at: '2026-07-02 15:27', who: 'phycoextract v0.4', action: 'extracted' }],
  },
  {
    id: 'ex-0009',
    paperId: 'SP-001',
    sectionId: 's4',
    quote: 'The pH excursion to 8.3 is the principal weakness of the configuration',
    field: 'ph_setpoint',
    value: 8.3,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.64,
    status: 'rejected',
    organism: 'cw15',
    extractorRun: 'v0.3',
    rejectReason: 'not this field',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-06-11 08:55', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-06-24 13:18',
        who: 'S. Creighton',
        action: 'rejected',
        from: 'ph_setpoint',
        to: 'terminal pH, not a controlled setpoint',
      },
    ],
  },
  {
    id: 'ex-0010',
    paperId: 'SP-001',
    sectionId: 's2',
    quote: 'a final potassium phosphate concentration of 1.61 g L⁻¹',
    field: 'medium_component_conc',
    value: 1.61,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'potassium phosphate',
    gold: { value: 1.61, unit: 'g L⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-18 10:04',
        who: 'S. Creighton',
        action: 'gold annotation added (no extraction)',
      },
    ],
  },
  // ---------------------------------------------------------------- SP-002
  {
    id: 'ex-0011',
    paperId: 'SP-002',
    sectionId: 's3',
    quote: 'the cultures grew with a specific growth rate of 0.104 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.104,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.104, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:31', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 14:02', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0012',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: 'contained 4.84 g L⁻¹ Tris base',
    field: 'medium_component_conc',
    value: 4.84,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Tris base',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:29', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 14:05', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0013',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: 'raised the nitrogen source to 0.750 g L⁻¹ ammonium chloride',
    field: 'medium_component_conc',
    value: 0.75,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'ammonium chloride',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:29', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 14:07', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0014',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: 'incubated at 24 °C under continuous illumination',
    field: 'temperature',
    value: 24,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 09:30', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-16 14:09', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0015',
    paperId: 'SP-002',
    sectionId: 's3',
    quote: 'The high-buffer variant grew at 0.109 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.109,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.87,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 09:32', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0016',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: 'glacial acetic acid to 2.10 g L⁻¹',
    field: 'medium_component_conc',
    value: 2.1,
    unit: 'mg L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.62,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'acetic acid',
    extractorRun: 'v0.3',
    audit: [{ at: '2026-06-11 09:14', who: 'phycoextract v0.3', action: 'extracted' }],
  },
  {
    id: 'ex-0017',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: '0.050 g L⁻¹ calcium chloride dihydrate',
    field: 'medium_component_conc',
    value: 0.05,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.74,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'calcium chloride',
    extractorRun: 'v0.3',
    audit: [{ at: '2026-06-11 09:14', who: 'phycoextract v0.3', action: 'extracted' }],
  },
  {
    id: 'ex-0018',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: 'Flasks were incubated at 24 °C under continuous illumination',
    field: 'ph_setpoint',
    value: 7,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.58,
    status: 'unverified',
    organism: 'cw15',
    gold: { value: 7, unit: '' },
    extractorRun: 'v0.3',
    audit: [{ at: '2026-06-11 09:15', who: 'phycoextract v0.3', action: 'extracted' }],
  },
  {
    id: 'ex-0019',
    paperId: 'SP-002',
    sectionId: 's2',
    quote: '0.100 g L⁻¹ magnesium sulfate heptahydrate',
    field: 'medium_component_conc',
    value: 0.1,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'magnesium sulfate',
    gold: { value: 0.1, unit: 'g L⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-18 10:19',
        who: 'S. Creighton',
        action: 'gold annotation added (no extraction)',
      },
    ],
  },
  // ---------------------------------------------------------------- SP-003
  {
    id: 'ex-0020',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'cw15 grew at 0.132 h⁻¹ in mixotrophic culture',
    field: 'growth_rate_mu',
    value: 0.132,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.96,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.132, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:02', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 09:20', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0021',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'the photoautotrophic rate for cw15 was 0.061 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.061,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.94,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.061, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:02', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 09:22', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0022',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'reached a final biomass density of 1.95 g L⁻¹ at 48 h',
    field: 'final_biomass_density',
    value: 1.95,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:03', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 09:25', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0023',
    paperId: 'SP-003',
    sectionId: 's2',
    quote: 'a photon flux density of 150 µmol m⁻² s⁻¹ at the vessel surface',
    field: 'light_intensity',
    value: 150,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 10:01', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 09:27', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0024',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'cc1690 reached only 0.052 h⁻¹ under photoautotrophic conditions',
    field: 'growth_rate_mu',
    value: 0.052,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.84,
    status: 'unverified',
    organism: 'cc1690',
    extractorRun: 'v0.4',
    audit: [{ at: '2026-07-02 16:08', who: 'phycoextract v0.4', action: 'extracted' }],
  },
  {
    id: 'ex-0025',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'photoautotrophic cultures plateaued at 0.74 g L⁻¹',
    field: 'final_biomass_density',
    value: 0.74,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.82,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 10:04', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0026',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'total protein reached 29 % DW by the Lowry method',
    field: 'protein_content',
    value: 29,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.77,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'Lowry',
    extractorRun: 'v0.4',
    audit: [{ at: '2026-07-02 16:09', who: 'phycoextract v0.4', action: 'extracted' }],
  },
  {
    id: 'ex-0027',
    paperId: 'SP-003',
    sectionId: 's3',
    quote: 'cc1690 grew at 0.097 h⁻¹ under the same mixotrophic conditions',
    field: 'growth_rate_mu',
    value: 0.079,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.66,
    status: 'rejected',
    organism: 'cc1690',
    gold: { value: 0.097, unit: 'h⁻¹' },
    extractorRun: 'v0.3',
    rejectReason: 'wrong value',
    corrected: { value: 0.097, unit: 'h⁻¹' },
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-06-11 10:41', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-06-24 14:02',
        who: 'S. Creighton',
        action: 'rejected',
        from: 0.079,
        to: 0.097,
      },
    ],
  },
  // ---------------------------------------------------------------- SP-004
  {
    id: 'ex-0028',
    paperId: 'SP-004',
    sectionId: 's3',
    quote: 'a protein content of 38 % DW in nitrogen-replete cultures',
    field: 'protein_content',
    value: 38,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.94,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Lowry',
    gold: { value: 38, unit: '% DW' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 11:15', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 15:31', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0029',
    paperId: 'SP-004',
    sectionId: 's3',
    quote: 'protein had fallen to 17 % DW after 48 h of nitrogen starvation',
    field: 'protein_content',
    value: 17,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Lowry',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 11:16', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 15:33', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0030',
    paperId: 'SP-004',
    sectionId: 's3',
    quote: 'The replete cultures grew at 0.112 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.112,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.112, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-14 11:15', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-17 15:35', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0031',
    paperId: 'SP-004',
    sectionId: 's2',
    quote: 'maintained at 25 °C in an illuminated orbital incubator',
    field: 'temperature',
    value: 25,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.87,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-14 11:13', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0032',
    paperId: 'SP-004',
    sectionId: 's3',
    quote: 'All cultures were held at 25 °C throughout the shift',
    field: 'temperature',
    value: 25,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.7,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4',
    audit: [{ at: '2026-07-02 17:22', who: 'phycoextract v0.4', action: 'extracted' }],
  },
  {
    id: 'ex-0033',
    paperId: 'SP-004',
    sectionId: 's3',
    quote: 'the residual rate under nitrogen limitation was 0.038 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.038,
    unit: 'd⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.6,
    status: 'unverified',
    organism: 'cw15',
    gold: { value: 0.038, unit: 'h⁻¹' },
    extractorRun: 'v0.3',
    audit: [{ at: '2026-06-11 11:37', who: 'phycoextract v0.3', action: 'extracted' }],
  },
  {
    id: 'ex-0034',
    paperId: 'SP-004',
    sectionId: 's2',
    quote: 'ammonium chloride was reduced to 0.094 g L⁻¹',
    field: 'medium_component_conc',
    value: 0.094,
    unit: 'mg L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.68,
    status: 'rejected',
    organism: 'cw15',
    componentTag: 'ammonium chloride',
    extractorRun: 'v0.4',
    rejectReason: 'wrong unit',
    corrected: { value: 0.094, unit: 'g L⁻¹' },
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-02 17:20', who: 'phycoextract v0.4', action: 'extracted' },
      {
        at: '2026-07-19 08:47',
        who: 'S. Creighton',
        action: 'rejected',
        from: 'mg L⁻¹',
        to: 'g L⁻¹',
      },
    ],
  },
  {
    id: 'ex-0035',
    paperId: 'SP-004',
    sectionId: 's3',
    quote: 'an intermediate value of 24 % DW at 24 h',
    field: 'protein_content',
    value: 24,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    componentTag: 'Lowry',
    gold: { value: 24, unit: '% DW' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-19 09:02',
        who: 'S. Creighton',
        action: 'gold annotation added (no extraction)',
      },
    ],
  },
  // ---------------------------------------------------------------- SP-005
  {
    id: 'ex-0036',
    paperId: 'SP-005',
    sectionId: 's3',
    quote: 'the maximum specific growth rate of 0.141 h⁻¹ was reached at 150 µmol m⁻² s⁻¹',
    field: 'growth_rate_mu',
    value: 0.141,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.96,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.141, unit: 'h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-15 08:41', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-18 13:05', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0037',
    paperId: 'SP-005',
    sectionId: 's3',
    quote: 'a final biomass density of 2.24 g L⁻¹ at 60 h',
    field: 'final_biomass_density',
    value: 2.24,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-15 08:42', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-18 13:08', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0038',
    paperId: 'SP-005',
    sectionId: 's2',
    quote: 'the highest treatment delivered 900 µmol m⁻² s⁻¹ measured at the liquid surface',
    field: 'light_intensity',
    value: 900,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.81,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4',
    audit: [{ at: '2026-07-02 18:03', who: 'phycoextract v0.4', action: 'extracted' }],
  },
  {
    id: 'ex-0039',
    paperId: 'SP-005',
    sectionId: 's3',
    quote: 'cultures at 20 µmol m⁻² s⁻¹ grew at 0.071 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.071,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.85,
    status: 'unverified',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-15 08:43', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0040',
    paperId: 'SP-005',
    sectionId: 's3',
    quote: 'chlorophyll fell to 33 mg g⁻¹ at the highest photon flux',
    field: 'protein_content',
    value: 33,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.57,
    status: 'unverified',
    organism: 'cw15',
    componentTag: 'Lowry',
    extractorRun: 'v0.3',
    audit: [{ at: '2026-06-11 12:09', who: 'phycoextract v0.3', action: 'extracted' }],
  },
  {
    id: 'ex-0041',
    paperId: 'SP-005',
    sectionId: 's4',
    quote: 'The saturating rate of 0.141 h⁻¹ was not exceeded at higher photon flux',
    field: 'growth_rate_mu',
    value: 0.141,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.72,
    status: 'rejected',
    organism: 'cw15',
    extractorRun: 'v0.4r',
    rejectReason: 'duplicate',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-15 08:44', who: 'phycoextract v0.4r', action: 'extracted' },
      {
        at: '2026-07-18 13:14',
        who: 'S. Creighton',
        action: 'rejected',
        from: 'ex-0041',
        to: 'duplicate of ex-0036',
      },
    ],
  },
  {
    id: 'ex-0042',
    paperId: 'SP-005',
    sectionId: 's3',
    quote: 'Photoinhibited cultures grew at 0.089 h⁻¹',
    field: 'growth_rate_mu',
    value: 0.089,
    unit: 'h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'cw15',
    gold: { value: 0.089, unit: 'h⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-18 13:20',
        who: 'S. Creighton',
        action: 'gold annotation added (no extraction)',
      },
    ],
  },
];
