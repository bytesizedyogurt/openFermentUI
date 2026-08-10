// Corpus set C — SP-012 … SP-016 (corpus), SP-017 … SP-020 (demo shelf),
// records ex-0091 … ex-0132.
// All content is synthetic: fictional authors, invented venues, no real DOIs.
// Section text is authored first; every record.quote is copied verbatim from it
// (BUILD-SPEC invariant 1). record.si is recomputed in src/data/records.ts.
import type { Paper, ExtractionRecord } from '../types';

export const PAPERS_C: Paper[] = [
  {
    id: 'SP-012',
    title:
      'Methanol feeding policy, not construct dosage, governs specific productivity in fed-batch Komagataella phaffii GS115: DO-stat, fixed-exponential and hybrid induction compared at matched biomass',
    authors: [
      'Tomás Iriarte Quiroga',
      'Anneke van Rensburg',
      'Hiroto Sugimura',
      'Fatima Zahra Benjelloun',
      'Lars-Ove Thunberg',
    ],
    year: 2020,
    venue: 'Yeast Bioprocess Engineering Quarterly',
    organisms: ['gs115'],
    topics: ['methanol induction', 'feeding strategy', 'fed-batch', 'specific productivity'],
    abstract:
      'Methanol is simultaneously the inducer of the AOX1 promoter and a carbon and energy source, so in Komagataella phaffii the feeding policy sets the transcriptional state, the growth rate and the oxidative burden of the culture at once. We compared three induction policies — a dissolved-oxygen stat, a fixed exponential feed and a hybrid that switches between them — in 30 L fed-batch cultures of GS115 secreting the fungal lipase RlpB-3, with all three induced at the same biomass concentration and on the same medium. The hybrid policy delivered the highest titre and the highest mean specific productivity, while the fixed exponential feed accumulated the most biomass and the least product. On-line residual methanol explains the ordering: the fixed exponential feed spent most of the induction phase below the concentration needed to saturate AOX1 transcription. We report the full set of reactor set points so that the productivity figures can be reused as design assumptions rather than as headline claims.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Komagataella phaffii is used industrially for secreted recombinant proteins because it grows to very high cell density on inexpensive defined mineral salts and because the AOX1 promoter provides a tight induction switch that costs nothing to actuate beyond the inducer itself. That switch is also the principal liability of the platform. Methanol is the inducer and a carbon and energy source at the same time, so the feed rate sets the transcriptional state of the culture, the specific growth rate, the oxygen demand and the intracellular flux of formaldehyde and hydrogen peroxide simultaneously. A policy that maximises biomass is therefore not the policy that maximises specific productivity, and much of the spread in published titres for this host reflects a spread in feeding policy rather than in strain, construct or copy number.\n\n' +
          'Three policies dominate practice. A dissolved-oxygen stat couples the methanol pump to the dissolved-oxygen signal and feeds whenever oxygen rises above a threshold, which keeps residual methanol low and self-limits when oxygen transfer saturates. A fixed exponential feed sets the addition rate a priori from a target specific growth rate and an assumed yield coefficient, which is reproducible and easy to validate but blind to the actual state of the culture. A hybrid begins under oxygen control and hands over to a fixed ramp once the reactor reaches its oxygen transfer ceiling.\n\n' +
          'Comparisons between these policies are common, but they are rarely made at matched biomass. Because specific productivity is a per-gram quantity and titre is not, a policy that simply grows more cells can appear superior on titre while being inferior per gram of catalyst, and the two conclusions lead to different reactor sizing and to different capital estimates.\n\n' +
          'We therefore fixed the biomass concentration at the transition to induction, fixed the medium, the temperature and the pH set points, and varied only the methanol addition policy. Residual methanol was measured on-line so that the transcriptional argument could be tested directly rather than inferred from the outcome, and every set point is reported so that the comparison can be reproduced or contested on its conditions rather than on its conclusions.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Komagataella phaffii GS115 carrying a single chromosomal copy of a secreted fungal lipase, designated RlpB-3, under the control of the AOX1 promoter was used throughout. Working cell banks were prepared from a single colony, verified by cassette-flanking PCR, and stored in glycerol at −80 °C. Seed cultures were grown in buffered glycerol complex medium and transferred at ten per cent by volume into 30 L stirred-tank reactors operated at a 20 L working volume.\n\n' +
          'The batch medium was a defined mineral salts formulation. The batch medium contained 40 g L⁻¹ glycerol as the sole carbon source, together with 18.2 g L⁻¹ potassium sulfate, magnesium sulfate heptahydrate, calcium sulfate and phosphoric acid, and was supplemented after sterilisation with a filter-sterilised trace metal solution and biotin. The batch and glycerol fed-batch phases were run at 30.0 °C. pH was held at 5.0 by on-demand addition of 28 % ammonium hydroxide, which also served as the sole nitrogen source. Dissolved oxygen was maintained above 25 % of air saturation by a cascade of agitation, air flow and oxygen enrichment.\n\n' +
          'Once the batch glycerol was exhausted, indicated by a sharp rise in dissolved oxygen, a glycerol fed-batch phase of four hours brought every reactor to the same biomass concentration before induction. The temperature set point was lowered to 25.0 °C at the start of methanol induction and held there for the remainder of the run.\n\n' +
          'Three induction policies were then applied. The dissolved-oxygen stat pulsed methanol whenever dissolved oxygen exceeded 30 % of saturation, with a fixed pulse volume and a minimum inter-pulse interval. The fixed exponential feed delivered methanol at a rate calculated for a target specific growth rate of 0.02 h⁻¹ and an assumed yield coefficient. The hybrid policy ran the dissolved-oxygen stat for the first eighteen hours of induction and then switched to a fixed ramp held at the mean rate observed over that window.\n\n' +
          'Residual methanol in the broth was measured on-line every two minutes by a headspace semiconductor sensor calibrated daily against gas chromatography of filtered broth. Off-gas was cooled in a condenser held at 4 °C before analysis, and the condensate was returned to the reactor. Biomass was determined gravimetrically in triplicate by drying washed pellets to constant mass, and secreted lipase was quantified by densitometry of reduced sodium dodecyl sulfate gels against a purified standard of known concentration.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'All three reactors reached the induction transition within twenty minutes of one another and at a dry cell weight of 41 g L⁻¹, so the comparison that follows is at matched biomass and matched medium history.\n\n' +
          'The DO-stat policy reached a final titre of 12.4 g L⁻¹ of RlpB-3 after 72 h of induction. Over the same induction period and on the same medium, the fixed exponential feed reached only 8.7 g L⁻¹, despite finishing with the highest biomass of the three reactors. The hybrid policy reached 14.9 g L⁻¹, the highest of the three, and did so with the shortest cumulative period of oxygen limitation.\n\n' +
          'Specific productivity separates the policies more sharply than titre does. Mean specific productivity under the hybrid policy was 3.6 mg g⁻¹ h⁻¹ across the induction phase, against 2.9 mg g⁻¹ h⁻¹ for the DO-stat over the same window. The fixed exponential feed sustained only 2.1 mg g⁻¹ h⁻¹, and its profile declined steadily after the first day rather than holding a plateau.\n\n' +
          'Biomass at the end of induction was 96 g L⁻¹ dry cell weight under the DO-stat policy, while the fixed exponential feed finished highest at 108 g L⁻¹ and the hybrid finished lowest at 88 g L⁻¹. The ordering of biomass is exactly the reverse of the ordering of specific productivity. Biomass yield on methanol during induction was 0.36 g g⁻¹ for the DO-stat and 0.44 g g⁻¹ for the fixed exponential feed, while over the preceding glycerol phases the yield on glycerol was 0.52 g g⁻¹ in all three reactors, as expected for a phase in which the policies had not yet diverged.\n\n' +
          'The on-line residual methanol traces account for the ordering. The fixed exponential feed held residual methanol below 0.4 g L⁻¹ for fifty-one of the seventy-two induction hours, which is below the concentration at which AOX1 transcription saturates in this strain, so a growing fraction of the carbon it delivered was consumed by cells that were only partially induced. The DO-stat oscillated between 0.8 and 2.6 g L⁻¹ with a period of roughly twelve minutes, and the hybrid held a smoother band once it left oxygen control. No reactor exceeded 4 g L⁻¹ residual methanol at any point, so growth inhibition by the inducer can be excluded as an explanation for any of the differences reported here.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The practical conclusion is that the feeding policy, and not the construct, sets specific productivity in this system. All three reactors carried the same single-copy cassette, the same medium and the same induction biomass, and they differed by a factor of 1.7 in mean specific productivity. Any comparison of constructs that does not hold the feeding policy fixed is therefore uninterpretable, and a titre reported without its feeding policy is not a reusable design assumption.\n\n' +
          'The mechanism we infer is transcriptional rather than metabolic. Residual methanol under the fixed exponential feed sat below the saturating concentration for most of the induction phase, and the resulting culture was a mixture of fully induced and partially induced cells rather than a uniformly induced population. That interpretation is consistent with the inverse ordering of biomass and specific productivity: carbon that does not go into product goes into cells.\n\n' +
          'Two limitations bound the conclusion. First, we used a single secreted lipase with a modest folding burden, and a protein that stresses the secretory pathway would be expected to invert part of the argument, because for such products the optimum residual methanol is set by folding capacity rather than by promoter occupancy. Second, our oxygen transfer ceiling was reached at around 90 g L⁻¹ dry cell weight, which is low for this platform; a reactor with a higher transfer coefficient would let the dissolved-oxygen stat run further before handing over.\n\n' +
          'We deliberately do not report a single recommended feed rate. The hybrid policy performed best here because it tracked the culture while oxygen transfer allowed it to and then held the rate that the culture had itself selected, and that is a control philosophy rather than a number. What transfers between facilities is the philosophy and the residual methanol window it produced, not the pump setting. For the same reason we report the residual methanol traces alongside the titres, since the concentration in the broth is the variable the promoter actually responds to and the only one that can be compared between reactors of different oxygen transfer capability.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-013',
    title:
      'Mixed glycerol-methanol feeding decouples growth from induction in Komagataella phaffii GS115 secreting a fungal phytase',
    authors: [
      'Ngozi Adeyemi-Clarke',
      'Sébastien Marchetti',
      'Pavla Doubková',
      'Yusuf Bakırcı',
      'Mei-Ling Chou',
    ],
    year: 2018,
    venue: 'International Journal of Yeast Bioprocessing',
    organisms: ['gs115'],
    topics: ['mixed feed', 'co-feeding', 'promoter regulation', 'fed-batch'],
    abstract:
      'Methanol-only induction of the AOX1 promoter forces a single feed to satisfy growth, maintenance and product formation, which caps specific productivity at the point where the culture can no longer oxidise methanol fast enough to meet its maintenance demand. Co-feeding a second carbon source separates those duties, but glycerol represses the promoter at high concentration and the practical window is narrow. We mapped that window for Komagataella phaffii GS115 secreting the fungal phytase PhyG-1, running 15 L fed-batch cultures at four glycerol-to-methanol mass ratios under otherwise identical conditions. A ratio of one part glycerol to four parts methanol raised titre by three quarters over methanol-only induction and nearly doubled specific productivity, while a one-to-one ratio suppressed product formation almost completely. Transcript measurements confirm that the suppression is promoter repression rather than a metabolic or oxygen limitation, and we report the residual glycerol concentration at which repression begins.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'The AOX1 promoter is attractive because it is tight, but tightness has a cost. Under methanol-only induction the same feed must supply the carbon for maintenance, the carbon for any residual growth, and the reducing power consumed by the peroxisomal oxidation of methanol itself, which is thermodynamically wasteful because the first oxidation step yields no ATP. At high cell density a large fraction of the methanol delivered to the reactor is therefore spent on maintenance rather than on product, and the specific productivity of the culture falls as biomass rises even though the promoter remains fully induced.\n\n' +
          'Co-feeding is the standard response. A second carbon source supplies maintenance energy and lets the methanol feed be dedicated to induction, which in principle raises product yield on methanol and lowers the oxygen demand per gram of product. Sorbitol and mannitol are non-repressing and are often preferred for that reason, but both are considerably more expensive than glycerol and neither is available at commodity scale in every region. Glycerol is cheap and is already used for the growth phase of essentially every process on this host, so a glycerol co-feed requires no new raw material qualification.\n\n' +
          'The obstacle is that glycerol represses the AOX1 promoter. Repression is concentration-dependent rather than absolute, so there exists a co-feeding window in which glycerol meets maintenance demand while remaining below the concentration at which it silences transcription. The width of that window determines whether glycerol co-feeding is practical, and it is rarely reported because most studies fix a single ratio and report the outcome. Titres above 20 g L⁻¹ have been claimed for constitutive promoter systems on this host, usually for cytosolic products and rarely with a closed carbon balance, and such claims are not directly comparable to an inducible process operated under a co-feed.\n\n' +
          'We therefore ran a ratio series rather than a single condition, held every other set point constant, and measured residual glycerol and AOX1 transcript abundance alongside titre, so that a productivity change could be attributed to repression or excluded from it on evidence rather than by argument.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Komagataella phaffii GS115 carrying a chromosomally integrated expression cassette for the secreted fungal phytase PhyG-1 under the AOX1 promoter was used throughout, with the alpha-factor prepro sequence as the secretion leader. Fermentations were run in 15 L stirred-tank reactors at a 10 L working volume, inoculated to an initial optical density at 600 nm of 1.0 from an overnight shake-flask seed.\n\n' +
          'The defined batch medium supplied glycerol at 45 g L⁻¹ together with ammonium sulfate at 12.0 g L⁻¹, potassium phosphate, magnesium sulfate and a filter-sterilised trace metal solution added after sterilisation. Antifoam was dosed automatically on a conductivity trigger rather than pre-added, so that the surfactant load at induction was equal across reactors. pH was maintained at 5.5 throughout by addition of ammonium hydroxide, and dissolved oxygen was held above 30 % of air saturation by cascaded agitation and oxygen enrichment.\n\n' +
          'The batch phase was run at 30.0 °C. The induction phase was run at a reduced set point of 28.0 °C, chosen from preliminary work as the temperature at which secreted phytase activity in the broth was most stable over a four-day induction without an unacceptable loss of specific growth rate.\n\n' +
          'Four co-feeding conditions were compared, defined by the mass ratio of glycerol to methanol in the combined feed: methanol only, one part glycerol to nine parts methanol, one to four, and one to one. The two carbon sources were delivered from separate reservoirs by independently calibrated pumps rather than as a premixed solution, so that the ratio could be verified gravimetrically during the run. Total carbon delivery rate was matched between conditions on a carbon-mole basis, so that the comparison isolates the ratio rather than the total feed rate.\n\n' +
          'Residual glycerol and methanol were determined every four hours by high-performance liquid chromatography on filtered broth with refractive index detection. AOX1 transcript abundance was measured by reverse-transcription quantitative PCR on samples taken at six-hour intervals, normalised to two reference transcripts selected for stability across the carbon regimes. Phytase activity was assayed colorimetrically as phosphate released from sodium phytate, and converted to a mass titre against a purified standard of known specific activity. Dry cell weight was determined gravimetrically in triplicate from 5 mL samples washed twice in deionised water.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Methanol-only induction gave 6.2 g L⁻¹ of PhyG-1 after 94 h, with a specific productivity that fell by half between the first and the fourth day of induction. Co-feeding at a glycerol-to-methanol mass ratio of one to four raised the final titre to 10.8 g L⁻¹ over the same induction period, and the corresponding volumetric productivity over the induction phase was 0.115 g L⁻¹ h⁻¹. The intermediate one-to-nine ratio gave 9.1 g L⁻¹, close enough to the one-to-four result that the optimum is broad on the low-glycerol side.\n\n' +
          'The one-to-one ratio behaved differently in kind rather than in degree. Titre collapsed to 1.4 g L⁻¹, and AOX1 transcript abundance fell more than thirtyfold within eight hours of the ratio change, recovering only after the glycerol feed was stopped. Residual glycerol in that reactor rose above 1.2 g L⁻¹ and stayed there, whereas in the one-to-four and one-to-nine reactors it remained below the detection limit of 0.05 g L⁻¹ throughout. We take 1.2 g L⁻¹ residual glycerol as an upper bound on the repression threshold, and note that the threshold is a concentration rather than a feed ratio: the same ratio applied to a culture with a higher maintenance demand would have been consumed rather than accumulated.\n\n' +
          'Specific productivity followed titre. Mean specific productivity at the one-to-four ratio was 5.2 mg g⁻¹ h⁻¹, against 2.9 mg g⁻¹ h⁻¹ under methanol-only induction, and the co-fed profile held a plateau through the third day rather than declining from the first. Biomass rose modestly with glycerol supply: the co-fed cultures reached 112 g L⁻¹ dry cell weight at the one-to-four ratio, against 97 g L⁻¹ for methanol-only induction, and biomass yield on the combined carbon feed was 0.44 g g⁻¹ at that ratio.\n\n' +
          'Oxygen demand per gram of product fell by a third at the one-to-four ratio relative to methanol-only induction, which is the expected consequence of shifting maintenance carbon away from the peroxisomal oxidation route. This matters for scale-up independently of the titre benefit, because oxygen transfer is the binding constraint on this platform at high cell density, and any reduction in oxygen demand per gram of product translates directly into a larger workable batch in a vessel of fixed transfer capability.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'Glycerol co-feeding works on this host, but the operating variable is the residual glycerol concentration and not the feed ratio. That distinction is the practical content of this paper. A ratio is a property of the pumps; a residual concentration is a property of the culture, and it is the residual concentration that the promoter reads. A process transferred between facilities on a ratio specification will drift into repression whenever the receiving reactor has a lower maintenance demand, a lower cell density or a cooler induction temperature, all of which reduce glycerol consumption without changing the pump setting.\n\n' +
          'The width of the window we measured is encouraging. Between the one-to-nine and one-to-four ratios the titre changed by less than twenty per cent, so the process is not knife-edged on the low-glycerol side, and repression appeared only once residual glycerol became measurable at all. A control strategy that feeds glycerol on demand against an on-line residual signal, rather than on a fixed ratio, would therefore capture most of the benefit with a wide margin against repression.\n\n' +
          'Two caveats limit the generalisation. First, phytase is a robust, heavily glycosylated secreted enzyme that tolerates a long induction; a product with a shorter half-life in the broth would shift the optimum toward shorter, more intense inductions where the co-feed benefit is smaller. Second, our comparison matched total carbon delivery on a carbon-mole basis, which is the right control for a mechanistic question but not necessarily the right control for an economic one, since glycerol and methanol differ both in price per carbon mole and in oxygen demand per carbon mole.\n\n' +
          'Finally, the transcript data should be read as evidence about mechanism, not as a calibration. Transcript abundance and secreted activity are separated by translation, folding, processing and export, and we observed the transcript collapse several hours before the titre curve flattened. Any control scheme built on transcript measurement would need that lag characterised for the specific product, and we would not expect the lag measured for a small, robust hydrolase to transfer to a large multidomain protein.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-014',
    title:
      'A 1,200 L high-cell-density fed-batch process for a secreted recombinant albumin in Komagataella phaffii GS115 with oxygen transfer as the binding constraint',
    authors: [
      'Oluwaseun Fadipe',
      'Katarzyna Wiśniewska-Bąk',
      'Rahul Venkataraman',
      'Émilie Rocheleau',
      'Duc Minh Tran',
    ],
    year: 2023,
    venue: 'Industrial Fermentation and Scale-Up Reports',
    organisms: ['gs115'],
    topics: ['high cell density', 'scale-up', 'oxygen transfer', 'recombinant albumin'],
    abstract:
      'High-cell-density operation of Komagataella phaffii is limited by oxygen transfer long before it is limited by nutrient supply, and the point at which the constraint binds moves with reactor geometry rather than with the strain. We describe a fed-batch process for the secreted recombinant albumin rALB-7 taken from 30 L through 300 L to a 1,200 L production vessel, with the methanol feed placed under a transfer-limited control law that holds the culture at the oxygen ceiling of the vessel itself instead of at a fixed feed rate. The process reached a final dry cell weight of 128 g L⁻¹ and a titre of 25.8 g L⁻¹ at 1,200 L, marginally above the 300 L result, and the productivity difference between scales is fully accounted for by the difference in volumetric oxygen transfer coefficient. We report the transfer coefficients, the set points and the yields so that the process can be re-sized against a different vessel.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'A fed-batch process for Komagataella phaffii is, at high cell density, an oxygen transfer process with a yeast attached to it. Methanol oxidation is heavily oxygen-demanding, and above roughly 80 g L⁻¹ dry cell weight the achievable feed rate in most production vessels is set by the volumetric oxygen transfer coefficient rather than by anything the organism is doing. This has a specific consequence for scale-up: a feed profile developed in a small, intensely agitated laboratory reactor will over-feed a large vessel, drive dissolved oxygen to zero, and produce the fermentative by-products and the loss of secreted product integrity that follow from it.\n\n' +
          'The conventional response is to transfer the feed profile and to reduce it by a fixed factor, chosen conservatively. That works, in the sense that the run completes, but it leaves capacity unused whenever the large vessel is better than the conservative estimate, and it fails whenever the vessel is worse. Neither outcome is visible from the run record unless dissolved oxygen and off-gas are logged together, which is why the same scale-up is often repeated several times before a stable profile is found.\n\n' +
          'We took a different approach and placed the methanol feed under a control law that holds the culture at whatever oxygen transfer the vessel can actually deliver, measured continuously from the off-gas oxygen and carbon dioxide balance. The feed rate then becomes an output of the process rather than an input to it, and the same control law can be moved between vessels without retuning. The price is that batch duration is no longer fixed in advance and must be scheduled against a predicted rather than a specified endpoint.\n\n' +
          'Recombinant albumin is a useful test case for such a law because it is secreted at high titre, is straightforward to quantify in crude broth, and is sensitive enough to proteolysis that a process excursion shows up as a quality signal rather than only as a yield loss. A control law that protects product quality by construction can therefore be distinguished from one that merely avoids an obvious failure.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'The production strain was Komagataella phaffii GS115 carrying a single integrated copy of a codon-optimised gene for the secreted recombinant albumin rALB-7 under the AOX1 promoter, with the native propeptide replaced by the alpha-factor secretion leader. Working cell banks were qualified by whole-cell PCR, copy-number determination and a shake-flask expression check before release.\n\n' +
          'Three scales were operated with geometrically similar impellers: 30 L and 300 L development vessels and a 1,200 L production vessel, at working volumes of 20 L, 200 L and 800 L respectively. The batch charge supplied glycerol at 50 g L⁻¹ together with magnesium sulfate heptahydrate at 14.9 g L⁻¹, potassium sulfate, calcium sulfate and phosphoric acid; trace metals and biotin were added after sterilisation through a 0.2 µm filter. pH was controlled at 5.2 by addition of ammonium hydroxide, which also supplied nitrogen. The growth phase was run at 30.0 °C and the induction phase at 26.0 °C, the reduction being applied over thirty minutes at the transition.\n\n' +
          'Dissolved oxygen was held above 20 % of air saturation throughout. Volumetric oxygen transfer coefficients were determined at each scale by the dynamic gassing-out method in cell-free medium at the working agitation and aeration set points, and again in situ during induction from the off-gas oxygen balance. Air was enriched with pure oxygen on a cascade above the maximum agitation set point, with enrichment capped for safety.\n\n' +
          'Induction used a transfer-limited feed law. The methanol pump rate was adjusted every ninety seconds to hold the oxygen uptake rate, calculated on-line from the inlet and outlet gas composition, at ninety per cent of the transfer capacity estimated for the current agitation, aeration and enrichment state. Residual methanol was monitored by headspace sensor as a safety interlock rather than as the controlled variable, with the feed suspended if residual methanol exceeded 6 g L⁻¹.\n\n' +
          'Dry cell weight was determined gravimetrically in quadruplicate. Albumin titre in clarified broth was measured by reversed-phase chromatography against a purified reference, with monomer content determined in parallel by size-exclusion chromatography so that aggregation could be tracked. Proteolytic clipping was followed by capillary electrophoresis on reduced samples. Substrate consumption was closed against the pump gravimetry, and carbon balances across the whole induction phase closed to within seven per cent at all three scales.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'All three scales followed the same trajectory to the end of the glycerol fed-batch phase. Divergence began during induction, and it tracked the measured transfer capacity of each vessel exactly.\n\n' +
          'The 1,200 L vessel reached a final dry cell weight of 128 g L⁻¹ at the end of a 90 h induction, and a titre of 25.8 g L⁻¹ of rALB-7. The 300 L development vessel, which had the higher transfer coefficient of the two production-relevant scales, reached 22.3 g L⁻¹ over the same induction period at a final dry cell weight of 114 g L⁻¹. Volumetric productivity over the induction phase was 0.287 g L⁻¹ h⁻¹ in the production vessel; at the 300 L scale the induction-phase volumetric productivity was 0.248 g L⁻¹ h⁻¹.\n\n' +
          'Mean specific productivity in the production vessel was 4.9 mg g⁻¹ h⁻¹ over the induction phase, and the profile was flat to within ten per cent between the second and the fourth day. Biomass yield on methanol during induction was 0.39 g g⁻¹ in the production vessel, and did not differ significantly between scales, which is the expected result if the feed law is holding the same specific methanol uptake rate in each vessel.\n\n' +
          'The transfer measurements close the argument. Volumetric oxygen transfer coefficients under induction conditions were 310 h⁻¹ at 30 L, 265 h⁻¹ at 300 L and 198 h⁻¹ at 1,200 L. The feed law responded by delivering proportionally less methanol per litre in the larger vessel, so the specific methanol uptake rate was held constant while the batch simply took longer to reach the same biomass. Dissolved oxygen never fell below its set point at any scale, and no reactor required the residual-methanol interlock.\n\n' +
          'Product quality was scale-independent within the resolution of the assays. Monomer content at harvest was above 97 % in all runs, and reduced capillary electrophoresis showed no increase in clipped species at the largest scale despite its longer induction. This is the outcome the feed law is designed to protect: the excursions that generate clipped albumin in this system are oxygen-limitation events, and the control law prevents them by construction rather than by conservative under-feeding.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The result we want to emphasise is not the titre but its insensitivity to scale. A conventional fixed-profile transfer from 300 L to 1,200 L, with the usual conservative de-rating, would have delivered a lower titre in the production vessel and would have attributed the shortfall to scale-up losses. Under the transfer-limited law the production vessel actually finished marginally ahead, and the whole of the productivity difference between the scales is explained by a single measured quantity, the volumetric oxygen transfer coefficient, with no residual scale effect left to explain.\n\n' +
          'That has a design consequence. If oxygen transfer is the binding constraint and the feed law tracks it, then the return on capital spent on transfer capacity can be computed directly: a vessel with a higher coefficient completes the same batch in less time at the same yields, and its productivity advantage is proportional rather than merely favourable. Conversely, spending on strain improvement to raise specific productivity yields nothing at all unless transfer capacity is raised alongside it, because the culture is already consuming every mole of oxygen the vessel can deliver.\n\n' +
          'The limitations are practical rather than conceptual. The feed law depends on an accurate on-line oxygen uptake rate, which in turn depends on well-calibrated inlet and outlet gas analysis and on a gas-tight vessel; a leaking headplate seal produces a slow, plausible-looking drift in the computed uptake rate and will silently under-feed the culture. Batch duration is variable, which complicates scheduling in a multi-product facility, and the endpoint must be predicted from the accumulated feed rather than specified in advance.\n\n' +
          'We also did not test the law against a deliberately impaired vessel. Every reactor used here was well maintained and in specification, and the interesting failure mode of a control law that trusts its own measurement is the case where the measurement degrades gradually rather than obviously. A redundant estimate of the uptake rate derived from the base addition profile would be a cheap safeguard and is the obvious next step.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-015',
    title:
      'Seasonal volumetric and areal productivity of Arthrospira platensis in unlined outdoor raceways over a full production year',
    authors: [
      'Amina Cheikh Sidiya',
      'Peder Halvorsen',
      'Chiara Buonanno',
      'Rajeev Nandakumar',
      'Thandeka Mahlangu',
    ],
    year: 2019,
    venue: 'Open Pond Cultivation Reports',
    organisms: ['aplat'],
    topics: ['outdoor raceway', 'areal productivity', 'seasonal variation', 'harvest'],
    abstract:
      'Productivity figures for open raceway cultivation of Arthrospira platensis are usually reported for a single favourable season, which makes them unsuitable as the basis for an annual production model. We operated four 42 m² unlined raceways in semi-continuous mode for a full production year at one site, recording irradiance, culture temperature, pond depth, dilution rate and gravimetric biomass on every operating day. Volumetric productivity varied roughly threefold between the winter and summer quarters, and the annual mean fell well below any single-season figure. Culture temperature rather than irradiance explained most of the winter shortfall at this latitude, and the harvest step, an inclined vibrating screen exploiting the filamentous morphology of the organism, was the least seasonally sensitive part of the process. We report the operating conditions in full, including the pH control band and the incident photon flux density, so that the annual figures can be transferred to another site with an explicit correction rather than by assumption.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Arthrospira platensis is the only phototrophic microorganism produced at genuine commodity scale, and essentially all of that production is in open raceways. The economics of a raceway facility are governed by areal productivity, because the pond area sets the capital cost and the land requirement, while volumetric productivity determines the harvest duty and therefore a large part of the operating cost. Both quantities are strongly seasonal at any site outside the tropics, and both are routinely reported for the best months of the year.\n\n' +
          'The consequence is a systematic optimism in the literature that feeds directly into techno-economic models. A summer volumetric productivity, annualised without correction, over-predicts annual output by a factor that depends on latitude and on the winter temperature minimum. Because the same models are used to compare raceways with closed photobioreactors, and because closed systems are less seasonally sensitive per unit of installed capacity, the error is not neutral between the alternatives it is used to compare.\n\n' +
          'The high-pH, high-alkalinity medium in which this organism is grown is a further complication. It suppresses contamination and buffers the culture against the pH excursions that accompany photosynthetic carbon uptake, but it also sets the inorganic carbon speciation and hence carbon availability at a given sparge rate. A productivity quoted without the alkalinity and the pH control band is not comparable to one measured under a different carbonate regime, and neither is usually reported.\n\n' +
          'We therefore ran a full production year at a single site under an unchanged operating protocol, and we report the whole record rather than its best quarter. The measurements are deliberately ordinary: gravimetric biomass, pond temperature, incident irradiance and dilution rate, recorded on every operating day, with no attempt to optimise the protocol during the year. The intention is to provide an annual baseline that a model can use directly.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Four unlined earthen raceways of 42 m² each were operated at a single inland site, paddle-wheel mixed at a surface velocity of 0.25 m s⁻¹ and held at a nominal culture depth of 0.18 m, adjusted seasonally to compensate for evaporation. Ponds were inoculated in early spring from a common indoor seed train and thereafter maintained in semi-continuous mode without reinoculation.\n\n' +
          'The medium was a bicarbonate-based formulation supplying sodium bicarbonate at 16.8 g L⁻¹, sodium nitrate, dipotassium phosphate, potassium sulfate, sodium chloride, magnesium sulfate, iron sulfate and a micronutrient blend, made up in borehole water. Make-up water carried a background chloride load equivalent to 1.0 g L⁻¹ sodium chloride, which was accounted for when the formulation was compounded. Nutrients were replenished on a schedule keyed to the harvested biomass rather than to elapsed time.\n\n' +
          'Carbon dioxide was injected into the paddle-wheel draught tube on pH demand. The pH control band was 9.6 to 10.0 with a set point of 9.8, and gas was delivered through a sintered diffuser under a shallow sump that gave a contact depth of 0.6 m. Culture pH, dissolved oxygen and temperature were logged at five-minute intervals by immersed probes calibrated weekly against buffer and air standards.\n\n' +
          'Incident photosynthetically active radiation was recorded at one-minute intervals by a horizontally mounted quantum sensor on a mast beside the pond array. Peak midday photon flux density in the summer quarter reached 1,850 µmol m⁻² s⁻¹, and the corresponding winter peak was below a third of that value. Culture temperature was uncontrolled and followed the diel and seasonal cycle of the site.\n\n' +
          'Biomass was determined gravimetrically each operating morning by filtering a known volume through a pre-weighed woven polyester screen, rinsing with dilute acid to remove carbonate precipitate, and drying to constant mass. Harvest was by inclined vibrating screen with a 30 µm aperture, exploiting the filamentous morphology of the organism, and the harvested slurry was dewatered on a belt press before drying. Dilution rate was set each morning to return the pond to its target standing biomass after harvest, and both the harvested and the returned volumes were metered.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Volumetric productivity over the summer quarter averaged 0.0125 g L⁻¹ h⁻¹, corresponding to an areal productivity of 22.5 g m⁻² d⁻¹ at the operating depth. The winter quarter averaged less than a third of that figure, and the annual mean over all operating days was 0.0071 g L⁻¹ h⁻¹, which is the number a production model should use.\n\n' +
          'Standing biomass followed the same pattern. The ponds carried a mean standing biomass of 1.15 g L⁻¹ through the summer quarter and were held deliberately lower in winter, at around 0.62 g L⁻¹, because the light penetration depth no longer supported the higher density and cultures held above it bleached within days.\n\n' +
          'Temperature rather than irradiance explains most of the seasonal difference at this site. Mean midday culture temperature in the summer quarter was 28 °C, within the range at which this organism grows without stress, whereas winter midday temperatures fell below 16 °C on more than half of the operating days and the ponds spent most of the night below 10 °C. Regressing daily productivity on integrated daily photon dose alone left a large seasonal residual; adding a temperature term removed most of it.\n\n' +
          'Specific growth rate measured over the twenty-four hours following each harvest averaged 0.62 d⁻¹ in the summer quarter, falling to roughly a third of that in winter. Because the ponds were operated semi-continuously rather than as batches, this rate is a post-dilution recovery rate rather than an unrestricted maximum, and we report it as such so that it is not mistaken for a strain property.\n\n' +
          'The harvest step was the most seasonally stable part of the process. Across the year the inclined screen recovered 92 % of the standing biomass presented to it, with no systematic seasonal trend and with the residual loss dominated by short filaments passing the aperture rather than by screen blinding. Blinding did occur during two summer weeks in which an unusually high proportion of the filaments were short and fragmented, and recovery fell to 78 % during that period before returning to baseline after a dilution-rate adjustment.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The annual mean volumetric productivity we measured is roughly forty per cent of the summer figure, and it is the summer figure that appears in most comparisons. Any model that annualises a single favourable season for this organism at this latitude will over-predict output by more than a factor of two, and the error propagates directly into the estimated minimum selling price, because capital is sized on area while revenue is sized on annual output.\n\n' +
          'The dominant seasonal variable at our site is temperature, not light. That ordering is site-specific and should not be transferred: at a lower latitude with a mild winter, irradiance would dominate and the seasonal ratio would be much narrower. What does transfer is the method, which is to regress daily productivity on both integrated photon dose and a temperature term and to report the residual, rather than to report a single mean and a standard deviation that conflates the two effects.\n\n' +
          'Pond depth is the one operating variable we would change with hindsight. We held a nominal 0.18 m through the year and compensated for the winter light limitation by lowering the standing biomass instead. Reducing the depth in winter would have raised the mean photon flux per cell at the same standing biomass and would probably have recovered part of the shortfall, at the cost of a larger diel temperature swing in a shallower pond, which at our winter minima might have made matters worse. We did not test it, and we would not recommend it without a paired trial.\n\n' +
          'The harvest data are the most directly reusable numbers here. The screen recovery we measured was insensitive to season, to standing biomass and to pond temperature, and depended almost entirely on the filament length distribution. A facility whose culture fragments, for whatever reason, should expect the harvest step rather than the growth step to become its limiting problem, and should size its screen area against the fragmented case rather than the nominal one.',
      },
    ],
    ingest: 'complete',
  },
  {
    id: 'SP-016',
    title:
      'Protein content and assay dependence in Arthrospira platensis as a function of nitrate supply and harvest phase',
    authors: [
      'Marisol Quintanilla Rojas',
      'Bilal Chaudhry',
      'Elin Sørhaug',
      'Kenji Watanabe',
      'Grace Wambui Kariuki',
      'Ivo Brandão Teixeira',
    ],
    year: 2021,
    venue: 'Journal of Algal Nutrition and Composition',
    organisms: ['aplat'],
    topics: ['protein content', 'nitrogen supply', 'compositional analysis', 'harvest timing'],
    abstract:
      'Protein contents reported for Arthrospira platensis span more than twenty percentage points of dry weight, and the spread is commonly attributed to strain or to geography. We show that most of it is attributable to two controllable factors: the nitrate status of the culture at harvest and the assay used to score protein. Cultures were grown in bicarbonate medium under controlled indoor conditions at four nitrate supply rates and sampled at three points in the growth curve, with protein measured in parallel by Kjeldahl nitrogen and by the Lowry method on aliquots of the same dried biomass. Nitrogen-replete exponential biomass reached a protein content well above the value obtained from the same culture after ten days of nitrate depletion, and the two assays disagreed by several percentage points on every sample. We recommend that any database record of protein content carry both the nitrogen status and the assay, since neither is recoverable from the number alone.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Arthrospira platensis is sold principally as a protein source, so its protein content is the single compositional number that determines its value. Reported values span from below forty-five per cent of dry weight to above seventy, a range wide enough that a purchaser cannot infer the protein content of a delivered lot from the literature at all. The spread is usually explained by strain differences or by production geography, both of which are difficult to test and neither of which is actionable for a producer.\n\n' +
          'Two more mundane explanations are available and are testable. The first is nitrogen status. This organism accumulates cyanophycin and phycobiliprotein as nitrogen reserves when nitrogen is plentiful and degrades them when it is not, so protein content falls steeply during nitrogen limitation while carbohydrate content rises to compensate. A pond replenished on a schedule keyed to elapsed time rather than to harvested biomass will drift into and out of nitrogen limitation, and its protein content will drift with it.\n\n' +
          'The second is the assay. Kjeldahl and Dumas methods measure nitrogen and convert it to protein through a factor that assumes a fixed nitrogen content of the protein fraction and no non-protein nitrogen, which is a poor assumption for an organism that stores nitrogen in non-protein forms. Dye-binding and Lowry-type assays measure something closer to peptide bonds, but they require complete extraction from a cell that is not trivially lysed, and they are calibrated against a standard protein whose response differs from that of the sample.\n\n' +
          'We separated the two effects by controlling nitrate supply, sampling at defined points in the growth curve, and running two assays in parallel on aliquots of the same dried and milled biomass, so that extraction and calibration differences could not be confounded with sampling differences.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Arthrospira platensis was grown in 8 L flat-panel vessels under continuous artificial illumination in a temperature-controlled room. The medium was a bicarbonate formulation supplying sodium bicarbonate at 16.8 g L⁻¹, dipotassium phosphate, potassium sulfate, sodium chloride, magnesium sulfate, calcium chloride, iron sulfate and a micronutrient blend. Nitrogen was supplied as sodium nitrate at 2.5 g L⁻¹ in the replete condition, with three further conditions at one half, one fifth and one twentieth of that concentration and all other components unchanged.\n\n' +
          'Cultures were held at 32 °C by a jacketed water loop and illuminated from one face at an incident photon flux density of 180 µmol m⁻² s⁻¹, measured at the vessel surface before inoculation and again after each run. pH was maintained at 9.5 by on-demand injection of carbon dioxide into the sparge line against a dead band of 0.15 units. Vessels were sparged with air at 0.1 vvm and inoculated to a starting biomass of 0.15 g L⁻¹ from a common seed culture.\n\n' +
          'Each condition was sampled at three points: mid-exponential growth, the end of exponential growth, and after ten days of stationary phase during which no further nitrate was supplied. Biomass for compositional analysis was harvested on a 30 µm screen, washed twice with ammonium formate to remove medium salts, freeze-dried and milled to pass a 250 µm sieve. Every compositional measurement was made on aliquots of this common milled powder, so that the two assays saw identical material.\n\n' +
          'Total nitrogen was determined by Kjeldahl digestion and converted to protein using a nitrogen-to-protein factor of 5.95, which is the factor appropriate to this organism rather than the generic 6.25. Protein was determined in parallel by the Lowry method after alkaline extraction with three freeze-thaw cycles, calibrated against bovine serum albumin prepared in the same extraction buffer. Total carbohydrate was measured by the phenol-sulfuric acid method and residual nitrate in the medium by ion chromatography. All analyses were run in triplicate on independent aliquots of the milled powder.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Nitrogen status dominated the compositional response. Biomass from the nitrogen-replete condition harvested at the end of exponential growth had a protein content of 62.4 % DW by Kjeldahl. The same culture sampled after ten days of nitrate depletion returned 48.1 % DW, a loss of more than fourteen percentage points, with total carbohydrate rising by a closely matching amount over the same interval.\n\n' +
          'The assay contributed a smaller but systematic offset in the opposite direction. On the same replete end-of-exponential biomass, the Lowry assay returned 57.6 % DW, consistently below the Kjeldahl figure across every condition and every sampling point. The offset narrowed but did not disappear in the depleted samples, which is what would be expected if part of the Kjeldahl excess is non-protein nitrogen that is itself depleted during starvation.\n\n' +
          'Standing biomass at the end of exponential growth was 2.4 g L⁻¹ in the replete condition and fell monotonically with nitrate supply, reaching 0.9 g L⁻¹ in the most severely limited condition. Residual nitrate in the replete vessels was still measurable at the end of exponential growth and fell below the detection limit within four days of stationary phase, which fixes the point at which the compositional decline began.\n\n' +
          'The intermediate nitrate conditions behaved as a graded series rather than as a threshold. Protein content at the end of exponential growth fell approximately linearly with the logarithm of the supplied nitrate concentration across the four conditions, and the two assays tracked each other through that series with an almost constant offset. Pigment content followed protein closely, as expected given that phycobiliproteins account for a substantial fraction of the total, and the visible bleaching of the limited cultures was quantitatively consistent with the measured protein loss rather than being an independent stress response.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The two effects we separated are of different kinds and need different remedies. Nitrogen status is a process variable and can be controlled: a replenishment schedule keyed to harvested biomass rather than to elapsed time holds the culture replete, and the 62.4 % DW obtained from replete end-of-exponential biomass is achievable in production rather than being a laboratory artefact. Assay choice is a reporting variable and cannot be controlled away; it can only be declared.\n\n' +
          'Our recommendation is therefore narrow and practical. A protein content for this organism should be recorded with the assay named and the nitrogen status of the culture stated, because neither can be recovered from the number afterwards, and the two together account for most of the range in the published literature. A database that stores protein content as a single number against a strain identifier is storing an unusable quantity.\n\n' +
          'The nitrogen-to-protein factor deserves a separate comment. We used 5.95 rather than the generic 6.25, which lowers every Kjeldahl figure by about five per cent relative to the conventional calculation. Much of the older literature uses the generic factor, so a comparison between our numbers and those is a comparison between two different calculations of the same measurement, and roughly a third of the offset we observed between Kjeldahl and Lowry disappears if the generic factor is substituted.\n\n' +
          'The limitations are the single strain and the indoor, constant-illumination conditions. Outdoor cultures experience a diel cycle in which carbohydrate accumulates during the day and is consumed at night, so the harvest hour becomes a third variable that we did not test and that would be expected to move protein content by several percentage points within a single day. A producer selling on a protein specification should therefore fix the harvest hour as well as the replenishment schedule.',
      },
    ],
    ingest: 'complete',
  },

  // ── demo shelf (held out of the corpus for the ingest demo, §8.5) ──────
  {
    id: 'SP-017',
    title:
      'Nitrogen limitation shifts carbon partitioning from protein to storage lipid in Chlamydomonas reinhardtii cw15 without an immediate growth-rate penalty',
    authors: [
      'Yohannes Tesfamariam',
      'Klaudia Sobieraj',
      'Renaud Béliveau',
      'Sun-Hee Yoo',
      'Alessandra Moretti',
    ],
    year: 2017,
    venue: 'Algal Physiology and Bioprocess Notes',
    organisms: ['cw15'],
    topics: ['nitrogen limitation', 'lipid accumulation', 'carbon partitioning', 'two-stage cultivation'],
    abstract:
      'Two-stage cultivation, in which biomass is accumulated under nitrogen-replete conditions and then starved to trigger lipid accumulation, is the standard route to storage lipid in green algae. The cost of the second stage is usually stated as a loss of growth, but the timing of that loss is rarely resolved. We followed carbon partitioning in Chlamydomonas reinhardtii cw15 through a controlled step change from nitrogen-replete to nitrogen-free medium in continuously illuminated bioreactors, sampling at two-hour intervals for the first day. Specific growth rate was unchanged for the first twenty hours after the step, while neutral lipid began to accumulate within six hours and total protein began to fall within ten. The apparent grace period is not free: it is paid for by degradation of the existing protein pool rather than by reduced carbon fixation, which has consequences for any process that intends to sell both the protein and the lipid fraction of the same biomass.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'Storage lipid in green algae is a stress product. Under nitrogen-replete growth the cell directs fixed carbon into protein and membrane, and only when nitrogen becomes limiting does it divert acetyl units into triacylglycerol, which serves as a carbon and energy sink that does not require nitrogen. The two-stage process exploits this directly: grow the culture to high density with nitrogen available, then remove nitrogen and allow the cells to convert the carbon they continue to fix into lipid.\n\n' +
          'The cost of the second stage is normally described in aggregate, as a loss of productivity relative to a hypothetical culture that continued to grow. That framing hides the question a process designer actually needs answered, which is when the loss begins. If growth continues for a useful period after the nitrogen step, the second stage can be shortened and overlapped with the first, and the reactor time spent producing nothing is small. If growth stops immediately, the second stage is pure conversion and its duration must be justified entirely by the value of the lipid.\n\n' +
          'The question is also a compositional one. A process that sells the protein fraction as well as the lipid fraction has an interest in knowing whether the lipid is made from newly fixed carbon or from the recycled carbon skeletons of degraded protein, because in the second case the two products trade against each other directly and the total value of the biomass may not rise at all.\n\n' +
          'We therefore resolved the transition at a two-hour sampling interval, in continuously illuminated reactors under otherwise constant conditions, with growth rate, total protein, total carbohydrate and neutral lipid measured on the same samples so that the carbon balance could be closed across the step.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Chlamydomonas reinhardtii cw15 was grown photoautotrophically in 3 L jacketed glass bioreactors at a working volume of 2.4 L, illuminated continuously from two sides by white light-emitting diode panels at an incident photon flux density of 260 µmol m⁻² s⁻¹. Culture temperature was held at 25.0 °C and pH at 7.2 by on-demand injection of carbon dioxide into the sparge gas, which was otherwise air at 0.2 vvm.\n\n' +
          'The growth medium was a nitrate-based minimal formulation supplying potassium nitrate at 1.0 g L⁻¹ together with phosphate, magnesium, calcium and a chelated trace metal mixture. Cultures were inoculated from exponential-phase seed and allowed to grow for three days before the step change, by which point residual nitrate was still above eighty per cent of its initial value and the cultures were unambiguously nitrogen-replete.\n\n' +
          'The step change was made by continuous diafiltration rather than by centrifugation and resuspension, in order to avoid the mechanical and dark stress that accompanies a pellet-and-resuspend protocol. Culture was circulated through a hollow-fibre module at a modest transmembrane pressure while nitrogen-free medium of otherwise identical composition was fed at the permeate rate, so that the volume and the biomass concentration were unchanged and the residual nitrate fell below the detection limit within forty minutes. A replete control culture was subjected to the identical diafiltration against nitrate-containing medium.\n\n' +
          'Samples were taken every two hours for the first thirty hours after the step and every six hours thereafter. Dry cell weight was determined gravimetrically in duplicate on 25 mL samples. Total protein was measured by the Lowry method after alkaline extraction, total carbohydrate by the phenol-sulfuric acid method, and neutral lipid gravimetrically after chloroform-methanol extraction with an internal standard added before extraction. Cell number and mean cell volume were recorded on an electrical-impedance counter, and residual nitrate in the medium was followed by ion chromatography throughout.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Specific growth rate was indistinguishable between the starved and the replete cultures for the first twenty hours after the step, at which point the starved cultures began to diverge and their growth rate fell steadily to near zero over the following day. Cell number continued to increase through the first eighteen hours, so the maintained growth rate reflects continued division rather than cell enlargement alone.\n\n' +
          'Neutral lipid began to accumulate well before growth slowed. A measurable rise above the replete control was detectable six hours after the step, and by twenty-four hours the neutral lipid content of the starved biomass had roughly doubled relative to the control. The accumulation was approximately linear in time through the first two days and then decelerated as the cultures became light-limited by their own increasing density and pigment loss.\n\n' +
          'Total protein per gram of dry weight began to fall ten hours after the step and had declined by a quarter at twenty-four hours. The timing is the important observation: protein degradation began while growth rate was still unaffected, so the first lipid the cells accumulated was being assembled at least in part from carbon released by the turnover of existing protein rather than exclusively from newly fixed carbon.\n\n' +
          'Total carbohydrate rose transiently, peaking at around eight hours and falling back thereafter, which is consistent with starch acting as a temporary sink before the lipid pathway was fully engaged. The carbon balance closed to within nine per cent across the first forty-eight hours when protein, carbohydrate and lipid pools were summed against the gravimetric biomass and the integrated carbon uptake. Pigment content fell continuously from the fourth hour, and the cultures were visibly yellow by the end of the second day.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The apparent grace period after a nitrogen step is real but it is not free. Growth continued for twenty hours, which is long enough to be worth exploiting in a scheduling sense, but protein degradation began at ten hours and the earliest lipid was partly made from that recycled carbon. A process that sells only lipid can treat the grace period as a bonus. A process that sells a protein co-product cannot, because the two fractions are trading against one another from the tenth hour onward.\n\n' +
          'This has a direct implication for how two-stage processes should be timed. If protein is the primary product, the correct operation is not a two-stage process at all but a single nitrogen-replete stage harvested at the end of exponential growth. If lipid is the primary product and protein is a low-value residue, then a longer starvation is straightforwardly better. The difficult case is the intermediate one, where the optimum starvation time is set by the ratio of the two product prices and by the rate constants we report here, and it is genuinely sensitive to both.\n\n' +
          'Diafiltration rather than centrifugal washing was, in hindsight, essential to resolving the timing. In pilot experiments using a pellet-and-resuspend protocol we saw an immediate growth arrest that recovered over several hours and that we now attribute to the handling rather than to the nitrogen step. Any study reporting an instantaneous growth response to nutrient removal should be read with the washing method in mind.\n\n' +
          'The main limitation is that a single strain under constant illumination is not a production condition. Outdoor cultures experience a diel cycle that interacts strongly with storage metabolism, since starch and lipid pools are both consumed at night, and we would expect the clean separation of timescales we observed here to be blurred substantially under a natural light regime.',
      },
    ],
    ingest: 'shelf',
  },
  {
    id: 'SP-018',
    title:
      'Turbidostat operation of Chlamydomonas reinhardtii cw15 for steady-state estimation of light-limited kinetic parameters',
    authors: [
      'Nnamdi Okonkwo-Reyes',
      'Hanne Lindqvist',
      'Aarav Deshmukh',
      'Camille Tessier',
      'Zeynep Aydın Koç',
    ],
    year: 2022,
    venue: 'Continuous Culture and Control Letters',
    organisms: ['cw15'],
    topics: ['turbidostat', 'continuous culture', 'kinetic parameters', 'light limitation'],
    abstract:
      'Kinetic parameters for photoautotrophic algae are usually fitted to batch growth curves, where light availability, biomass concentration and nutrient status all change together and the fitted constants absorb whatever the model omits. We built a turbidostat in which biomass concentration is held constant by feedback on transmitted light, so that the incident photon flux can be stepped between steady states while every other variable is held fixed. Operating Chlamydomonas reinhardtii cw15 at seven photon flux set points, we obtained a light-response curve from steady-state dilution rates rather than from transient batch data, with each point measured over at least five residence times. The resulting saturation constant differs substantially from the value fitted to batch curves on the same strain in the same vessel, and the discrepancy is systematic rather than random. We describe the control loop and the steady-state criteria in enough detail for the measurement to be reproduced.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'A kinetic parameter is only as good as the experiment that produced it. For photoautotrophic growth the standard experiment is a batch culture followed to stationary phase, from which a maximum specific growth rate and a light saturation constant are fitted. The difficulty is that in a batch culture the biomass concentration rises monotonically, so the light available to an average cell falls monotonically, and the fitted saturation constant is therefore estimated from data in which the independent variable was never actually controlled.\n\n' +
          'Continuous culture removes that confound in principle. In a chemostat the dilution rate sets the growth rate and the culture finds its own steady-state biomass concentration, but for a light-limited culture that steady state is itself a function of the optical path and the biomass, so the light regime again varies with the operating point. A turbidostat inverts the control structure: biomass is held constant by feedback, the dilution rate becomes the measured output, and the light regime is fixed by construction because the optical density of the culture is fixed.\n\n' +
          'Turbidostats are less common than chemostats mainly because the feedback measurement is awkward. An in-line optical density probe fouls, and a probe that fouls slowly produces a slow drift in the controlled biomass that is invisible in the dilution rate record until it becomes large. Much of the engineering effort in this work went into a transmitted-light measurement that could be zeroed against a clean reference without interrupting the culture.\n\n' +
          'Our object was not to produce a better number for its own sake but to establish how different the number is when the confound is removed, since the same parameters are used in reactor design models where an error in the saturation constant translates directly into an error in the predicted depth of the productive zone.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'The turbidostat vessel was a 1.6 L flat-sided glass reactor with a 20 mm optical path, illuminated from one face by a dimmable white light-emitting diode panel and jacketed for temperature control. Working volume was held at 1.2 L by an overflow weir, and the culture was mixed by a magnetically coupled impeller at a rate verified not to damage the cells over a seven-day run.\n\n' +
          'Transmitted light was measured by a photodiode mounted on the rear face, sampled every ten seconds and referenced every six hours against a cell-free channel in the same optical block that was flushed with filtered permeate. The controller compared the transmitted signal against a set point corresponding to a dry cell weight of 0.85 g L⁻¹ and actuated a peristaltic feed pump; the overflow weir removed the corresponding volume. Feed and effluent were both weighed continuously, so the dilution rate was obtained gravimetrically rather than from pump calibration.\n\n' +
          'Medium was a nitrate-based minimal formulation, sterile-filtered rather than autoclaved to avoid precipitation, and supplied from a reservoir on a balance under a nitrogen headspace. Culture temperature was held at 25.0 °C, pH at 7.0 by carbon dioxide injection into the sparge line, and the sparge gas was air enriched to 1.5 % by volume carbon dioxide at 0.15 vvm.\n\n' +
          'Seven incident photon flux set points between 40 and 900 µmol m⁻² s⁻¹ were applied in a randomised order rather than in an ascending series, so that any slow drift in the culture would not be aliased onto the light response. A steady state was accepted only when the gravimetric dilution rate had varied by less than three per cent over five consecutive residence times and the offline dry cell weight agreed with the optical set point to within five per cent. Offline dry cell weight, cell number, pigment content and photosystem quantum yield were measured at each accepted steady state.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'The reactor held its biomass set point closely once the reference-channel flush interval was reduced to six hours. Over a fourteen-day continuous run the offline dry cell weight remained within four per cent of the target at every sampling point, and the drift attributable to window fouling was reduced to a level indistinguishable from the gravimetric noise.\n\n' +
          'Steady-state dilution rate rose steeply with incident photon flux at low light and saturated above roughly 400 µmol m⁻² s⁻¹. The maximum specific growth rate obtained from the plateau of the light-response curve was consistent between the ascending and descending randomised replicates, which argues against a slow acclimation artefact. At the lowest set point the culture washed in to a very low dilution rate but remained stable indefinitely, so the low-light end of the curve is a genuine steady state rather than an extrapolation.\n\n' +
          'The saturation constant fitted to the steady-state data was substantially higher than the value obtained by fitting the same model to batch growth curves collected in the same vessel with the same medium and the same inoculum. The direction of the discrepancy is what a self-shading argument predicts: in a batch culture, cells experience a declining mean flux as biomass accumulates, so the apparent response to incident flux is compressed and the fitted constant is biased low.\n\n' +
          'Pigment content per gram of dry weight varied more than twofold across the light series, rising at low flux and falling at high flux, which is the expected photoacclimation response. Because the turbidostat holds dry cell weight rather than optical density constant, that pigment change alters the attenuation at fixed biomass, and we corrected the mean flux estimate accordingly at each set point. Photosystem quantum yield was above 0.6 at every steady state, confirming that the cultures were light-limited rather than photodamaged even at the highest flux tested.',
      },
      {
        id: 's4',
        heading: 'Discussion',
        text:
          'The practical message is that a light saturation constant fitted to batch data is not the same quantity as one measured at steady state, and the two should not be interchanged in a design model. The batch value is systematically biased by self-shading, and the size of the bias depends on the optical path of the vessel in which the batch was run, so batch-derived constants are not even consistent between laboratories using different flask geometries.\n\n' +
          'That does not make batch data useless. A maximum specific growth rate estimated from the early exponential phase of a dilute batch culture is a well-conditioned measurement, and ours agreed with the turbidostat plateau to within the measurement error. It is specifically the saturation constant, which describes the shape of the response rather than its ceiling, that requires the light regime to be controlled rather than merely recorded.\n\n' +
          'The engineering lesson is about the reference channel. Our first configuration referenced the transmitted signal against a stored dark and clean reading taken at the start of the run, and it produced a biomass drift of nearly twenty per cent over ten days that was entirely invisible in the dilution-rate record, because the controller was faithfully holding a set point that had itself moved. A turbidostat that cannot re-reference against clean optics in situ should be regarded as an open-loop device with a slow disturbance.\n\n' +
          'The limitations are the single strain, the single optical path and the constant temperature. A thicker vessel would change the relationship between incident and mean flux and would require the same correction we applied here for pigment, and we have not tested whether the steady-state constant is invariant to that correction. A diel light regime would introduce a further complication that a turbidostat is poorly suited to study, since the control loop would be chasing a moving growth rate throughout the day.',
      },
    ],
    ingest: 'shelf',
  },
  {
    id: 'SP-019',
    title:
      'Phycocyanin retention during spray drying and freeze drying of Arthrospira platensis biomass at pilot scale',
    authors: [
      'Leandro Barbosa Pimentel',
      'Ines Haddadi',
      'Wiktor Zieliński',
      'Michiko Arakawa',
      'Sipho Ndlela',
    ],
    year: 2020,
    venue: 'Journal of Algal Downstream Processing',
    organisms: ['aplat'],
    topics: ['spray drying', 'pigment stability', 'downstream processing', 'food colourant'],
    abstract:
      'Phycocyanin is the highest-value component of Arthrospira platensis biomass and the least thermally stable, so the drying step largely determines whether a lot can be sold as a colourant or only as a protein meal. We compared pilot-scale spray drying at three inlet temperatures with tray freeze drying on splits of a single harvested slurry, tracking phycocyanin concentration, colour coordinates and protein solubility through drying and through twelve weeks of accelerated storage. Spray drying at the lowest workable inlet temperature retained most of the pigment present in the wet slurry, while the highest inlet temperature lost more than a third of it, almost all during the first second of atomisation rather than during the subsequent residence in the chamber. Freeze drying retained the most pigment but produced a powder whose storage stability was worse, which we attribute to its higher porosity and consequent oxygen exposure.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'The value of a lot of Arthrospira platensis biomass is set almost entirely by its phycocyanin content. As a natural blue colourant the pigment commands a price per kilogram far above that of the biomass it is extracted from, and a lot that fails a colourant specification is worth only its protein value, which is an order of magnitude less. The pigment is also the most fragile component of the biomass: it is a water-soluble chromoprotein that denatures at moderate temperature and bleaches on exposure to light and oxygen.\n\n' +
          'Drying is therefore the pivotal unit operation. The harvested slurry leaving a belt press is typically fifteen to twenty per cent dry solids and must reach below eight per cent moisture for stable storage, which is a large amount of water to remove from a heat-sensitive material. Spray drying is the standard industrial answer because it is continuous, cheap per tonne and produces a free-flowing powder, but the atomised droplet passes through a hot gas stream and the pigment does not always survive it. Freeze drying preserves the pigment but is expensive enough that it is used only for the highest-value fraction.\n\n' +
          'The literature comparison between the two is complicated by the fact that most published spray-drying results are reported by inlet temperature alone. Inlet temperature is not what the product experiences: the droplet is evaporatively cooled while free moisture remains, so the thermal history depends on the atomisation, the feed solids and the outlet temperature at least as much as on the inlet set point.\n\n' +
          'We therefore split a single harvested slurry, dried the splits by four routes on the same day, and measured not only the immediate pigment retention but also the storage stability of the resulting powders, since a drying route that preserves pigment at the outlet but produces an unstable powder has not actually solved the problem.',
      },
      {
        id: 's2',
        heading: 'Materials and Methods',
        text:
          'Biomass was harvested from a single 40 m² outdoor raceway on one morning by inclined screen followed by belt pressing, giving a slurry of 17.4 % dry solids that was held at 6 °C and processed within four hours. The slurry was divided into four equal splits, and a fifth aliquot was retained wet for the reference pigment assay.\n\n' +
          'Three splits were spray dried on a pilot co-current dryer with a two-fluid nozzle at inlet temperatures of 140, 165 and 190 °C, with the feed rate adjusted at each condition to hold the outlet temperature at 78 °C so that the residual moisture of the powders was matched. Atomising air pressure and nozzle geometry were unchanged between conditions. The fourth split was frozen at minus 40 °C in 12 mm trays and freeze dried over 36 h with a shelf temperature ramp to 25 °C and a chamber pressure below 20 Pa.\n\n' +
          'Phycocyanin was extracted from powders and from the wet reference by repeated freeze-thaw in phosphate buffer followed by centrifugation, and quantified spectrophotometrically from the absorbance at the phycocyanin and allophycocyanin maxima with a correction for scattering. Retention is reported relative to the wet reference on a dry-mass basis, so that moisture differences between powders cannot inflate it. Colour coordinates were measured on the dry powders under a standard illuminant, and protein solubility was determined as the fraction of total protein extractable into neutral buffer.\n\n' +
          'Accelerated storage was carried out in sealed amber vials at 40 °C and 60 % relative humidity for twelve weeks, with duplicate vials withdrawn at four-week intervals for pigment and colour measurement. Powder particle size was measured by laser diffraction, and bulk and tapped density were determined so that porosity could be estimated for each route.',
      },
      {
        id: 's3',
        heading: 'Results and Discussion',
        text:
          'Immediate pigment retention fell monotonically with inlet temperature. The 140 °C condition retained most of the phycocyanin present in the wet slurry, the 165 °C condition lost roughly a fifth, and the 190 °C condition lost more than a third. Because outlet temperature and residual moisture were matched across the three conditions, the difference cannot be attributed to the final state of the powder and must arise during the droplet trajectory.\n\n' +
          'Two observations locate the loss in the first moments after atomisation. First, the loss scaled with inlet temperature rather than with chamber residence time, which was similar across conditions. Second, a supplementary run in which the feed was atomised into an unheated chamber and collected wet showed no measurable pigment loss, excluding shear at the nozzle as a mechanism. The most likely explanation is that the outer shell of the droplet reaches gas temperature briefly before the evaporative flux establishes, and the pigment in that shell is denatured.\n\n' +
          'Freeze drying retained more pigment than any spray-dried condition, as expected. Its advantage did not survive storage. After twelve weeks of accelerated storage the freeze-dried powder had lost more pigment than the 140 °C spray-dried powder, ending below it despite starting above it. The freeze-dried material had roughly twice the porosity of the spray-dried powders and a much larger accessible surface, and we attribute the storage loss to oxidative bleaching through that open structure. Colour coordinates followed the pigment assay closely in every case, so a simple colour measurement is an adequate proxy for release testing.\n\n' +
          'Protein solubility told a different story from pigment retention and is worth reporting separately. It fell only slightly across all spray-dried conditions, including the hottest, so a lot that has failed a colourant specification because of pigment loss may still be perfectly acceptable as a soluble protein ingredient. The practical recommendation from this work is therefore to spray dry at the lowest inlet temperature the dryer throughput allows, to specify the outlet temperature rather than the inlet temperature in the process record, and to package for storage under conditions matched to the porosity of the powder rather than to a generic assumption.',
      },
    ],
    ingest: 'shelf',
  },
  {
    id: 'SP-020',
    title:
      'Techno-Economic Assessment of an Integrated Algal Biorefinery for Protein, Pigment and Lipid Co-Products (Two-Column Scanned Proceedings Reprint)',
    authors: [
      'Ravindra Selvakumar',
      'Anneli Rautiainen',
      'Gabriel Nwachukwu Eze',
      'Paloma Ferreiro Lens',
      'Tae-Jun Sohn',
    ],
    year: 2016,
    venue: 'Proceedings of the Regional Symposium on Applied Phycology',
    organisms: ['cw15', 'aplat'],
    topics: ['techno-economic analysis', 'biorefinery', 'co-products', 'capital cost'],
    abstract:
      'Single-product algal processes rarely clear their cost of capital, which has made the integrated biorefinery, in which one biomass stream is fractionated into several products of differing value, the standard proposal for making the economics work. This reprint of a symposium contribution presents a discounted cash-flow assessment of such a biorefinery producing a pigment concentrate, a food-grade protein isolate and a residual lipid stream from a common cultivation and harvest train. The assessment is built bottom-up from equipment-level capital estimates and a stream-level mass balance, with every physical assumption declared alongside the operating condition it was drawn from. Under the base case the pigment stream carries the project, contributing the majority of revenue from a small minority of the mass, and the protein isolate is marginal against its commodity alternative. Sensitivity analysis identifies pigment recovery through the extraction and drying train, rather than cultivation productivity, as the parameter that most strongly determines the outcome.',
    sections: [
      {
        id: 's1',
        heading: 'Introduction',
        text:
          'The case for an algal biorefinery is arithmetic before it is technical. A cultivation and harvest train has a cost per tonne of dry biomass that is largely independent of what the biomass is subsequently made into, and for closed or semi-closed systems that cost is well above the market price of any bulk commodity the biomass could substitute for. A single-product process must therefore either serve a high-value market that can absorb a small volume, or it must fail to clear its cost of capital. Fractionating one biomass stream into several products of differing value is the standard proposal for escaping that arithmetic.\n\n' +
          'The proposal is easy to state and difficult to assess, because the fractionation steps interact. A pigment extraction that maximises pigment recovery generally denatures the protein that would otherwise have been sold as an isolate; a lipid extraction that uses an aggressive solvent forecloses food-grade use of the residue. Assessments that treat the products as independent and simply add their revenues therefore systematically overstate the case.\n\n' +
          'A second difficulty is that the physical assumptions entering such an assessment come from different sources, measured under different conditions, and are combined without their conditions attached. A harvest recovery measured on a laboratory centrifuge, a disruption efficiency measured on a walled strain and a pigment yield measured on fresh rather than dried biomass can be multiplied together to produce a process yield that no real train would achieve.\n\n' +
          'The assessment presented here is built to make those assumptions visible. Every physical parameter is declared with its unit and the operating condition it was measured under, the mass balance is closed at the stream level rather than assumed, and the cost lines are computed per kilogram of each product so that they sum to the reported figure by construction rather than by reconciliation.',
      },
      {
        id: 's2',
        heading: 'Process configuration and cost basis',
        text:
          'The modelled facility cultivates biomass in a hybrid train of closed tubular reactors for seed and semi-closed raceways for bulk production, at a nameplate output of 1,200 tonnes of dry biomass per year. Harvest is by inclined screen and belt press for the filamentous organism and by disc-stack centrifugation for the unicellular organism, with the two cultivation lines kept separate through harvest and combined only at the dewatering step for costing purposes.\n\n' +
          'Downstream, the dewatered slurry is disrupted by bead milling and the lysate is clarified. A first aqueous extraction recovers the pigment fraction, which is ultrafiltered, diafiltered and spray dried to a colourant concentrate. The retained solids proceed to an alkaline protein extraction followed by isoelectric precipitation, giving a protein isolate that is neutralised and dried. The residue is solvent-extracted for lipid, and the final solids are sold as a low-value animal feed component or, where local regulation permits, digested for biogas.\n\n' +
          'Capital costs are estimated bottom-up at the equipment level from vendor quotations escalated to a common basis year, with installation, piping, instrumentation and civil works applied as factored allowances that differ by equipment class rather than as a single global factor. Cultivation area capital is estimated separately per square metre of pond and per metre of tube, since the two scale differently with plant size.\n\n' +
          'Operating costs are built from the stream-level mass balance. Media costs follow the recipe and the makeup rate implied by the harvest water return; utilities follow the pumping, mixing, refrigeration and drying duties computed from the balance rather than from a specific-energy assumption; labour is estimated from a shift structure sized to the number of controlled unit operations. The discounted cash-flow analysis uses a twenty-year plant life, a three-year construction period, straight-line depreciation and a real discount rate applied to constant-value cash flows, and reports the minimum selling price of the pigment concentrate that sets the net present value to zero at the assumed prices of the co-products.',
      },
      {
        id: 's3',
        heading: 'Results',
        text:
          'Under the base case the pigment stream carries the project. It accounts for a small minority of the product mass leaving the facility and the majority of the revenue, and the minimum selling price of the pigment concentrate is the figure to which the whole assessment is sensitive. The protein isolate contributes meaningfully to revenue but is priced against a commodity alternative that sets a hard ceiling, so improvements in protein recovery raise revenue only up to the point where the isolate displaces the entire addressable volume at that price.\n\n' +
          'The lipid stream does not pay for its own extraction step in the base case. Solvent recovery, the associated ventilation and containment capital, and the loss of food-grade status for the residue together exceed the value of the recovered lipid at the assumed price. A variant configuration that omits lipid extraction entirely and sends the post-protein residue directly to digestion improves the net present value, which is a result we did not expect and which we report despite its being unfavourable to the integrated concept.\n\n' +
          'On the capital side, the cultivation train dominates installed cost, as it does in every assessment of this kind, but it does not dominate the sensitivity. Because the pigment price is high and the pigment mass is small, a proportional change in cultivation productivity moves the outcome less than a proportional change in the fraction of pigment surviving the extraction and drying train. The chain of recoveries from harvest through disruption, extraction, membrane concentration and drying is multiplicative, and each individual step in it is reported in the literature with an uncertainty of several percentage points.\n\n' +
          'The sensitivity ranking is therefore led by pigment recovery through the downstream train, followed by the pigment price, the cultivation areal productivity and the discount rate, with capital cost per square metre of pond appearing only fifth. Harvest recovery enters twice, once directly and once through its effect on the water return and hence on media makeup, and its combined influence is larger than its position in the direct ranking suggests.',
      },
      {
        id: 's4',
        heading: 'Discussion and conclusions',
        text:
          'The central conclusion is that an integrated algal biorefinery of this configuration is a pigment business with three by-products, not a balanced portfolio. That framing matters because it changes what the operator should optimise and what the developer should measure before committing capital. Effort spent raising areal productivity is worth less at the margin than effort spent raising the fraction of pigment that survives from the pond to the drum, and the second quantity is measured far less often than the first.\n\n' +
          'It also changes what should be reported. A multiplicative chain of recoveries is only as trustworthy as its least well characterised link, and several of the links in this chain are routinely quoted without the conditions they were measured under. A disruption efficiency measured on a wall-deficient laboratory strain does not transfer to a walled production organism; a pigment extraction yield measured on fresh lysate does not transfer to material that has been dried and rehydrated. We have flagged in the assumption table every parameter whose source condition differs from the modelled condition, and there are more of them than we were comfortable with.\n\n' +
          'The negative result on lipid extraction deserves emphasis because it runs against the usual direction of these assessments. Adding a product to a biorefinery is not automatically value-accretive: it adds capital, it adds operating cost, and it can destroy the optionality of the streams it touches. The configuration question is therefore not how many products can be extracted but which subset of them clears its own incremental cost.\n\n' +
          'Finally, the reader should treat every absolute figure here as conditional on the price set, which was assembled from regional quotations in a single year and which moves considerably between years. The rankings and the structural conclusions are more robust than the numbers, and it is the rankings that we would defend.',
      },
    ],
    ingest: 'shelf',
  },
];

export const RECORDS_C: ExtractionRecord[] = [
  // ---------------------------------------------------------------- SP-012
  {
    id: 'ex-0091',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'reached a final titre of 12.4 g L⁻¹ of RlpB-3 after 72 h of induction',
    field: 'product_titer',
    value: 12.4,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'gs115',
    componentTag: 'recombinant lipase RlpB-3',
    gold: { value: 12.4, unit: 'g L⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 09:04', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 10:12', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-20 10:13', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0092',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'the fixed exponential feed reached only 8.7 g L⁻¹',
    field: 'product_titer',
    value: 8.7,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'gs115',
    componentTag: 'recombinant lipase RlpB-3',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 09:04', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 10:15', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0093',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'The hybrid policy reached 14.9 g L⁻¹, the highest of the three',
    field: 'product_titer',
    value: 14.9,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.88,
    status: 'unverified',
    organism: 'gs115',
    componentTag: 'recombinant lipase RlpB-3',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 09:05', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0094',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'Mean specific productivity under the hybrid policy was 3.6 mg g⁻¹ h⁻¹',
    field: 'specific_productivity',
    value: 3.6,
    unit: 'mg g⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.91,
    status: 'verified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-18 09:05', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 08:32', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0095',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'The fixed exponential feed sustained only 2.1 mg g⁻¹ h⁻¹',
    field: 'specific_productivity',
    value: 2.1,
    unit: 'mg g⁻¹ d⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.63,
    status: 'unverified',
    organism: 'gs115',
    gold: { value: 2.1, unit: 'mg g⁻¹ h⁻¹' },
    extractorRun: 'v0.4',
    audit: [
      { at: '2026-07-17 14:48', who: 'phycoextract v0.4', action: 'extracted' },
      { at: '2026-07-18 07:55', who: 'unit linter', action: 'flagged — unit basis disagrees with source span' },
    ],
  },
  {
    id: 'ex-0096',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'Biomass at the end of induction was 96 g L⁻¹ dry cell weight under the DO-stat policy',
    field: 'final_biomass_density',
    value: 96,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 09:06', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 10:19', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0097',
    paperId: 'SP-012',
    sectionId: 's2',
    quote: 'pH was held at 5.0 by on-demand addition of 28 % ammonium hydroxide',
    field: 'ph_setpoint',
    value: 5.0,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.87,
    status: 'unverified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 09:06', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0098',
    paperId: 'SP-012',
    sectionId: 's2',
    quote: 'Off-gas was cooled in a condenser held at 4 °C before analysis',
    field: 'temperature',
    value: 4,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.68,
    status: 'rejected',
    organism: 'gs115',
    extractorRun: 'v0.4',
    rejectReason: 'not a culture temperature — the span describes the off-gas condenser',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-17 14:50', who: 'phycoextract v0.4', action: 'extracted' },
      {
        at: '2026-07-20 10:24',
        who: 'S. Creighton',
        action: 'rejected — not a culture temperature — the span describes the off-gas condenser',
      },
    ],
  },
  {
    id: 'ex-0099',
    paperId: 'SP-012',
    sectionId: 's3',
    quote: 'the yield on glycerol was 0.52 g g⁻¹ in all three reactors',
    field: 'yield_biomass_substrate',
    value: 0.52,
    unit: 'g g⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'gs115',
    gold: { value: 0.52, unit: 'g g⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-22 11:05',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-013
  {
    id: 'ex-0100',
    paperId: 'SP-013',
    sectionId: 's3',
    quote: 'raised the final titre to 10.8 g L⁻¹',
    field: 'product_titer',
    value: 10.8,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.94,
    status: 'verified',
    organism: 'gs115',
    componentTag: 'recombinant phytase PhyG-1',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 10:21', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 13:40', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0101',
    paperId: 'SP-013',
    sectionId: 's3',
    quote: 'Methanol-only induction gave 6.2 g L⁻¹ of PhyG-1 after 94 h',
    field: 'product_titer',
    value: 6.2,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'gs115',
    componentTag: 'recombinant phytase PhyG-1',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 10:21', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 13:42', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0102',
    paperId: 'SP-013',
    sectionId: 's3',
    quote: 'the corresponding volumetric productivity over the induction phase was 0.115 g L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 0.115,
    unit: 'g L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-18 10:22', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 09:14', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0103',
    paperId: 'SP-013',
    sectionId: 's3',
    quote: 'Mean specific productivity at the one-to-four ratio was 5.2 mg g⁻¹ h⁻¹',
    field: 'specific_productivity',
    value: 5.2,
    unit: 'mg g⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.89,
    status: 'verified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-18 10:22', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 09:16', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0104',
    paperId: 'SP-013',
    sectionId: 's3',
    quote: 'the co-fed cultures reached 112 g L⁻¹ dry cell weight at the one-to-four ratio',
    field: 'final_biomass_density',
    value: 112,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.85,
    status: 'unverified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 10:23', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0105',
    paperId: 'SP-013',
    sectionId: 's2',
    quote: 'The induction phase was run at a reduced set point of 28.0 °C',
    field: 'ph_setpoint',
    value: 5.5,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.58,
    status: 'unverified',
    organism: 'gs115',
    extractorRun: 'v0.3',
    audit: [
      { at: '2026-06-29 16:37', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-07-18 07:58',
        who: 'span aligner',
        action: 'flagged — cited span does not contain the extracted quantity',
      },
    ],
  },
  {
    id: 'ex-0106',
    paperId: 'SP-013',
    sectionId: 's2',
    quote: 'The induction phase was run at a reduced set point of 28.0 °C',
    field: 'temperature',
    value: 28,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'unverified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 10:24', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0107',
    paperId: 'SP-013',
    sectionId: 's1',
    quote: 'Titres above 20 g L⁻¹ have been claimed for constitutive promoter systems',
    field: 'product_titer',
    value: 20,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.61,
    status: 'rejected',
    organism: 'gs115',
    componentTag: 'recombinant phytase PhyG-1',
    extractorRun: 'v0.3',
    rejectReason: 'background literature claim in the introduction, not a result of this study',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-06-29 16:38', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-07-20 13:51',
        who: 'S. Creighton',
        action: 'rejected — background literature claim in the introduction, not a result of this study',
      },
    ],
  },
  {
    id: 'ex-0108',
    paperId: 'SP-013',
    sectionId: 's3',
    quote: 'against 2.9 mg g⁻¹ h⁻¹ under methanol-only induction',
    field: 'specific_productivity',
    value: 2.9,
    unit: 'mg g⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'gs115',
    gold: { value: 2.9, unit: 'mg g⁻¹ h⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-22 11:12',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-014
  {
    id: 'ex-0109',
    paperId: 'SP-014',
    sectionId: 's3',
    quote: 'a titre of 25.8 g L⁻¹ of rALB-7',
    field: 'product_titer',
    value: 25.8,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.96,
    status: 'verified',
    organism: 'gs115',
    componentTag: 'recombinant albumin rALB-7',
    gold: { value: 25.8, unit: 'g L⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 11:40', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 15:02', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-20 15:03', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0110',
    paperId: 'SP-014',
    sectionId: 's3',
    quote: 'reached 22.3 g L⁻¹ over the same induction period',
    field: 'product_titer',
    value: 22.3,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'gs115',
    componentTag: 'recombinant albumin rALB-7',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 11:40', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 15:05', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0111',
    paperId: 'SP-014',
    sectionId: 's3',
    quote: 'a final dry cell weight of 128 g L⁻¹',
    field: 'final_biomass_density',
    value: 128,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 11:41', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-20 15:07', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0112',
    paperId: 'SP-014',
    sectionId: 's2',
    quote: 'The growth phase was run at 30.0 °C and the induction phase at 26.0 °C',
    field: 'temperature',
    value: 26,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.84,
    status: 'verified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-18 11:41', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 10:03', who: 'H. Ndlovu', action: 'verified — induction set point, not the growth phase value' },
    ],
  },
  {
    id: 'ex-0113',
    paperId: 'SP-014',
    sectionId: 's2',
    quote: 'pH was controlled at 5.2 by addition of ammonium hydroxide',
    field: 'ph_setpoint',
    value: 5.2,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.88,
    status: 'unverified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 11:42', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0114',
    paperId: 'SP-014',
    sectionId: 's3',
    quote: 'Mean specific productivity in the production vessel was 4.9 mg g⁻¹ h⁻¹',
    field: 'specific_productivity',
    value: 4.9,
    unit: 'mg g⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.86,
    status: 'unverified',
    organism: 'gs115',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 11:42', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0115',
    paperId: 'SP-014',
    sectionId: 's3',
    quote: 'at the 300 L scale the induction-phase volumetric productivity was 0.248 g L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 0.248,
    unit: 'g L⁻¹ d⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.6,
    status: 'unverified',
    organism: 'gs115',
    gold: { value: 0.248, unit: 'g L⁻¹ h⁻¹' },
    extractorRun: 'v0.4',
    audit: [
      { at: '2026-07-17 15:33', who: 'phycoextract v0.4', action: 'extracted' },
      { at: '2026-07-18 08:02', who: 'unit linter', action: 'flagged — time basis disagrees with source span' },
    ],
  },
  {
    id: 'ex-0116',
    paperId: 'SP-014',
    sectionId: 's2',
    quote: 'The batch charge supplied glycerol at 50 g L⁻¹',
    field: 'final_biomass_density',
    value: 50,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.57,
    status: 'rejected',
    organism: 'gs115',
    extractorRun: 'v0.3',
    rejectReason: 'span reports a medium component concentration, not a biomass density',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-06-29 17:12', who: 'phycoextract v0.3', action: 'extracted' },
      {
        at: '2026-07-21 10:11',
        who: 'H. Ndlovu',
        action: 'rejected — span reports a medium component concentration, not a biomass density',
      },
    ],
  },
  {
    id: 'ex-0117',
    paperId: 'SP-014',
    sectionId: 's3',
    quote: 'Biomass yield on methanol during induction was 0.39 g g⁻¹ in the production vessel',
    field: 'yield_biomass_substrate',
    value: 0.39,
    unit: 'g g⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'gs115',
    gold: { value: 0.39, unit: 'g g⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-22 11:20',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-015
  {
    id: 'ex-0118',
    paperId: 'SP-015',
    sectionId: 's3',
    quote: 'Volumetric productivity over the summer quarter averaged 0.0125 g L⁻¹ h⁻¹',
    field: 'volumetric_productivity',
    value: 0.0125,
    unit: 'g L⁻¹ h⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.93,
    status: 'verified',
    organism: 'aplat',
    gold: { value: 0.0125, unit: 'g L⁻¹ h⁻¹' },
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 13:15', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 11:40', who: 'S. Creighton', action: 'verified' },
      { at: '2026-07-21 11:41', who: 'S. Creighton', action: 'flagged for gold set' },
    ],
  },
  {
    id: 'ex-0119',
    paperId: 'SP-015',
    sectionId: 's3',
    quote: 'The ponds carried a mean standing biomass of 1.15 g L⁻¹ through the summer quarter',
    field: 'final_biomass_density',
    value: 1.15,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.89,
    status: 'verified',
    organism: 'aplat',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 13:15', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 11:44', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0120',
    paperId: 'SP-015',
    sectionId: 's2',
    quote: 'Peak midday photon flux density in the summer quarter reached 1,850 µmol m⁻² s⁻¹',
    field: 'light_intensity',
    value: 1850,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.91,
    status: 'verified',
    organism: 'aplat',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-18 13:16', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-22 08:50', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0121',
    paperId: 'SP-015',
    sectionId: 's2',
    quote: 'The pH control band was 9.6 to 10.0 with a set point of 9.8',
    field: 'ph_setpoint',
    value: 9.8,
    unit: '',
    si: { value: 0, unit: '' },
    confidence: 0.82,
    status: 'unverified',
    organism: 'aplat',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 13:16', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0122',
    paperId: 'SP-015',
    sectionId: 's3',
    quote: 'Mean midday culture temperature in the summer quarter was 28 °C',
    field: 'temperature',
    value: 28,
    unit: '°C',
    si: { value: 0, unit: '' },
    confidence: 0.78,
    status: 'unverified',
    organism: 'aplat',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 13:17', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0123',
    paperId: 'SP-015',
    sectionId: 's3',
    quote: 'averaged 0.62 d⁻¹ in the summer quarter',
    field: 'growth_rate_mu',
    value: 0.62,
    unit: 'd⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.72,
    status: 'unverified',
    organism: 'aplat',
    extractorRun: 'v0.4r',
    audit: [
      { at: '2026-07-18 13:17', who: 'phycoextract v0.4r', action: 'extracted' },
      {
        at: '2026-07-18 13:17',
        who: 'phycoextract v0.4r',
        action: 'note — source describes a post-dilution recovery rate',
      },
    ],
  },
  {
    id: 'ex-0124',
    paperId: 'SP-015',
    sectionId: 's2',
    quote: 'Make-up water carried a background chloride load equivalent to 1.0 g L⁻¹ sodium chloride',
    field: 'medium_component_conc',
    value: 1.0,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.64,
    status: 'rejected',
    organism: 'aplat',
    componentTag: 'sodium chloride',
    extractorRun: 'v0.4',
    rejectReason: 'the span describes the make-up water background, not a formulated medium component',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-17 16:05', who: 'phycoextract v0.4', action: 'extracted' },
      {
        at: '2026-07-21 11:52',
        who: 'S. Creighton',
        action: 'rejected — the span describes the make-up water background, not a formulated medium component',
      },
    ],
  },
  {
    id: 'ex-0125',
    paperId: 'SP-015',
    sectionId: 's3',
    quote: 'the inclined screen recovered 92 % of the standing biomass presented to it',
    field: 'harvest_recovery',
    value: 92,
    unit: '%',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'aplat',
    gold: { value: 92, unit: '%' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-22 11:31',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },

  // ---------------------------------------------------------------- SP-016
  {
    id: 'ex-0126',
    paperId: 'SP-016',
    sectionId: 's3',
    quote: 'had a protein content of 62.4 % DW by Kjeldahl',
    field: 'protein_content',
    value: 62.4,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.95,
    status: 'verified',
    organism: 'aplat',
    componentTag: 'Kjeldahl',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 14:22', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 14:05', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0127',
    paperId: 'SP-016',
    sectionId: 's3',
    quote: 'The same culture sampled after ten days of nitrate depletion returned 48.1 % DW',
    field: 'protein_content',
    value: 48.1,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.92,
    status: 'verified',
    organism: 'aplat',
    componentTag: 'Kjeldahl',
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      { at: '2026-07-18 14:22', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-21 14:07', who: 'S. Creighton', action: 'verified' },
    ],
  },
  {
    id: 'ex-0128',
    paperId: 'SP-016',
    sectionId: 's3',
    quote: 'the Lowry assay returned 57.6 % DW',
    field: 'protein_content',
    value: 57.6,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.9,
    status: 'verified',
    organism: 'aplat',
    componentTag: 'Lowry',
    extractorRun: 'v0.4r',
    reviewer: 'H. Ndlovu',
    audit: [
      { at: '2026-07-18 14:23', who: 'phycoextract v0.4r', action: 'extracted' },
      { at: '2026-07-22 09:31', who: 'H. Ndlovu', action: 'verified' },
    ],
  },
  {
    id: 'ex-0129',
    paperId: 'SP-016',
    sectionId: 's4',
    quote: 'the 62.4 % DW obtained from replete end-of-exponential biomass',
    field: 'protein_content',
    value: 62.4,
    unit: '% DW',
    si: { value: 0, unit: '' },
    confidence: 0.76,
    status: 'unverified',
    organism: 'aplat',
    componentTag: 'Kjeldahl',
    extractorRun: 'v0.4',
    audit: [
      { at: '2026-07-17 16:41', who: 'phycoextract v0.4', action: 'extracted' },
      { at: '2026-07-18 08:09', who: 'dedupe check', action: 'flagged as possible duplicate of ex-0126' },
    ],
  },
  {
    id: 'ex-0130',
    paperId: 'SP-016',
    sectionId: 's3',
    quote: 'Standing biomass at the end of exponential growth was 2.4 g L⁻¹ in the replete condition',
    field: 'final_biomass_density',
    value: 2.4,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.87,
    status: 'unverified',
    organism: 'aplat',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 14:24', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0131',
    paperId: 'SP-016',
    sectionId: 's2',
    quote: 'Nitrogen was supplied as sodium nitrate at 2.5 g L⁻¹ in the replete condition',
    field: 'medium_component_conc',
    value: 2.5,
    unit: 'g L⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0.88,
    status: 'unverified',
    organism: 'aplat',
    componentTag: 'sodium nitrate',
    extractorRun: 'v0.4r',
    audit: [{ at: '2026-07-18 14:24', who: 'phycoextract v0.4r', action: 'extracted' }],
  },
  {
    id: 'ex-0132',
    paperId: 'SP-016',
    sectionId: 's2',
    quote: 'illuminated from one face at an incident photon flux density of 180 µmol m⁻² s⁻¹',
    field: 'light_intensity',
    value: 180,
    unit: 'µmol m⁻² s⁻¹',
    si: { value: 0, unit: '' },
    confidence: 0,
    status: 'verified',
    organism: 'aplat',
    gold: { value: 180, unit: 'µmol m⁻² s⁻¹' },
    goldOnly: true,
    extractorRun: 'v0.4r',
    reviewer: 'S. Creighton',
    audit: [
      {
        at: '2026-07-22 11:44',
        who: 'S. Creighton',
        action: 'gold annotation added — no run proposed this span',
      },
    ],
  },
];
