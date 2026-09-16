# Saved input diagnostic (read only)

Input: `X_saved_input.blend`, SHA-256 `5FB5B96E5C629340FEC5CC2696E0861A5C0884A1F1E03BBFEAF9C608CB96CA79`.
Saved active mesh: `Cosha`, 3,646 vertices, bound to `CoshaRig`.
Canonical automatic match tolerance: `0.0000195056146423` in mesh-local units.

The current algorithm exactly reproduces: “Spatial symmetry could not pair source vertex 2671; 8 weighted source vertices are unmatched.” These are vertices **2671–2678**, an additional loop on the correct left upper arm, around 75% of the rest bone's length from shoulder to elbow. They all belong to the same positive-weight support component. This is asymmetric topology, with close opposite surface geometry but no coincident opposite vertices.

| Vertex | Local X | Local Y | Local Z | upper_arm.L weight | Reflected nearest vertex distance | Reflected nearest surface distance |
|---:|---:|---:|---:|---:|---:|---:|
|2671|0.2162545|0.1084691|-0.2017908|1.0000000|0.0413219|0.00103280|
|2672|0.2298912|0.1013207|-0.1881138|1.0000000|0.0418281|0.00118711|
|2673|0.2045265|0.0644174|-0.2129593|0.9985374|0.0374684|0.00028959|
|2674|0.2169725|0.0567628|-0.2012325|0.9990291|0.0354887|0.00026024|
|2675|0.2355834|0.0820223|-0.1811534|1.0000000|0.0386863|0.00133842|
|2676|0.2038925|0.1002076|-0.2136783|1.0000000|0.0413733|0.00163747|
|2677|0.2288789|0.0635579|-0.1871442|1.0000000|0.0371194|0.00120412|
|2678|0.1986909|0.0823374|-0.2185114|1.0000000|0.0396012|0.00003615|

All eight misses are on the bone-defined source half (+X). None are opposite-side or cross-midline contamination. Their nearest rest deform segment is `upper_arm.L`; source segment fractions are 0.7501–0.7595. Maximum opposite-surface discrepancy is approximately 0.71% of upper-arm bone length, while the missing vertex distances are much larger. Reflected triangular-surface barycentric sampling is geometrically plausible without editing mesh topology.

| Group | Positive support | Source / opposite / center | Edge-induced components | Entirely wrong-side islands | Strict source misses |
|---|---:|---|---:|---:|---:|
|upper_arm.L|117|117 / 0 / 0|1|0|8|
|upper_arm.R|115|115 / 0 / 0|1|0|10|
|forearm.L|108|108 / 0 / 0|1|0|2|
|forearm.R|107|107 / 0 / 0|1|0|0|
|hand.L|139|139 / 0 / 0|1|0|20|
|hand.R|126|126 / 0 / 0|1|0|19|
|shoulder.L|96|91 / 0 / 5|1|0|0|
|shoulder.R|106|101 / 0 / 5|1|0|10|

Support uses weight > `1e-8`, and connected components use only existing Mesh edges whose two endpoints both belong to that support. The detailed JSON lists every component vertex and weight. There is no fully opposite-side disconnected support island to remove in these eight groups in this saved file.

For L-to-R destination-driven surface sampling, ten right shoulder/upper-arm root vertices have nonzero sampled upper-arm weights without an exact source pair: 1705, 1873, 1886, 1894, 1916, 2617, 2626, 2631, 2632, 2633. Their source-surface distances range from 0.000270 to 0.004227. These weights also overlap the shoulder influence, so copying the upper-arm group alone needs a separate deform-budget decision; geometric correspondence alone does not imply that the existing no-total-change check will pass. Hand geometry additionally has 20 L and 19 R strict misses near the palm, thumb and finger bases; opposite-surface discrepancy reaches 0.006089 mesh-local units. A surface method should use bounded distance checks and report its interpolation count.

Validation: Blender 5.2 background with factory startup and autoexec disabled. Geometry (coordinates, edges, polygons, shape keys), every Vertex Group definition and membership, and the saved input file hash were identical before and after diagnosis. No blend file was saved. Detailed data: `saved_input_diagnostic.json`; reproducible script: `diagnose_saved.py`.
