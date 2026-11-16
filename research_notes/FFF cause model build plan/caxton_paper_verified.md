# Brion & Pattinson 2022 (CAXTON), checked against the paper text

Source read: the full text of Brion, D.A.J. & Pattinson, S.W., "Generalisable 3D printing error detection and correction via multi-head neural networks", *Nat. Commun.* 13, 4654 (2022), doi:10.1038/s41467-022-31985-y. I read it from the PMC copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/ (referred to below as [PMC]).

Access notes:
- www.nature.com: the proxy redirects to idp.nature.com, which it blocks with a 403. I could not read it.
- Supplementary Information PDF (MOESM1, which holds Fig. S1 with the learning rates and training plots), Peer Review File (MOESM2) and MOESM3: every request returned a reCAPTCHA page, so I could not read them.
- arXiv: export.arxiv.org returned a 403, and I found no arXiv preprint.
- **Figure contents I could not get:** Fig. 3b is the table of θmode/L/Imin/A+/A− values, and Fig. 2c holds the confusion matrices. Both are images. I quote only their captions.

## Data split and held-out evaluation

### Takeaway
The paper states a 0.7/0.2/0.1 train/validation/test split and nothing more. It does **not** say whether the split is by image, by print or by part. No held-out-print, held-out-part, held-out-printer or held-out-material test reports an accuracy number. Generalisation to new printers and materials is shown only through qualitative correction demos.

### Cited Findings
- Methods › Training procedure: "A training, validation, and test split of 0.7, 0.2 and 0.1, respectively, was used with a batch size of 32." The paper says nothing more about how the split was formed. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Dataset counts (Results › Dataset generation, filtering and augmentation):
  - 1,272,273 raw images. After removing failed prints by hand: "1,166,552 labelled images (91.7% of the original…)".
  - After dropping the post-update frames: 1,072,500.
  - After filtering outliers: 991,103.
  - After removing dark images (mean RGB < 10): "a cleaned dataset of 946,283 labelled images (74.4% of the original)".
  - The images come from 192 parts/prints. Abstract: "1.2 million images from 192 different parts". Intro: "from 192 prints of different 2D and 3D geometries".
  — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Training data hardware: eight Creality CR-20 Pro printers, with "each of which uses a different colour of feedstock" (Methods › CAXTON system), all printing PLA. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- The authors themselves name a leakage and confounding risk (Discussion): "there may be certain combinations of parameters which only appear in during a specific print or with a single colour of filament, and thus the network has learned these incorrect features as mappings." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- The test set is described only as "our test set" and "the diverse, multi-layer test set" (Results › Model architecture, training and performance). — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

### Inferences
- The split method is never stated. The paper does not mention grouping by print, and each 150-image block shares one parameter set. A random image-level split is therefore the most likely reading, and is what the repo code reportedly does. That would put near-duplicate neighbouring frames from the same print into both train and test, so the 84.3% figure is probably optimistic for unseen prints. This is my inference; the paper does not say it.
- Each printer had its own filament colour. Colour is therefore tied to printer, and the paper notes that colour can be tied to parameter combinations.

### Gaps
- Split unit (image, print or part): not stated.
- Accuracy on held-out prints, parts, printers or materials: not stated (none reported).
- Exact low/good/high bin limits: not stated in the main text, which says only that they were "selected based on our experience of AM with PLA". They may be in the SI or the code, which I could not read.

## Reported accuracies

### Takeaway
- Final test accuracy is 84.3% overall. Per head: flow rate 87.1%, lateral speed 86.4%, Z offset 85.5% and hotend 78.3%.
- These figures were measured on the filtered dataset, so the 15 frames after each update had already been removed. No unfiltered accuracy is given.
- Confusion matrices exist (Fig. 2c), but the values are not in the text.

### Cited Findings
- Accuracy at each stage, best seed (Results › Model architecture, training and performance):
  - Stage 1, single layer: "A training accuracy of 98.1% and validation accuracy of 96.6%".
  - Stage 2, full dataset: "training and validation accuracy of 91.1 and 85.4%".
  - Stage 3, balanced data with only the heads trained: "training accuracy of 89.2% and validation of 90.2%".
  — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Test results: "the final trained network was tested on our test set, where it achieved an overall accuracy of 84.3%. For each parameter, the classification accuracies on our test set were: flow rate 87.1%, lateral speed 86.4%, Z offset 85.5% and hotend temperature 78.3%." The paper does not define "overall". 84.3% is roughly the mean of the four head accuracies (84.3), so it is probably the mean per-head accuracy, not exact-match accuracy over all 81 combinations. That is my inference. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- The authors caveat the accuracy as understating usefulness. The example given: "a higher Z offset… can easily be mistaken as having a low flow rate—both appear as under extrusion… only one of these parameter combinations will be counted as 'correct'". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Fig. 2 caption: "c Confusion matrices of the final network after the three stages of training on our test dataset for each parameter. d Training and validation accuracy plots… across three seeds… on three datasets: single layer, full and balanced." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Table 1 (Methods): single-stage ResNets trained on the full dataset with one seed, test accuracy across four parameters:

  | Model | Test accuracy |
  |---|---|
  | ResNet18 | 80.4% |
  | ResNet34 | 82.5% |
  | ResNet50 | 81.8% |
  | ResNet101 | 81.4% |
  | This work | 84.3% |

  — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Multi-head versus single-head: "a ResNet18 model with a single head output for predicting flow rate achieved an accuracy of 77.5%. The same model with multiple heads… achieved… 82.1% at predicting flow rate" (after 50 epochs). The authors flag this as needing further experiments. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

### Inferences
- Hotend temperature is the weakest head (78.3%). Z offset is called "the primary weakness of the current dataset" in the Discussion, yet its accuracy (85.5%) is in line with the other heads.

### Gaps
- Per-class precision and recall, and the confusion-matrix cell values: these are only in the Fig. 2c image or the source-data zip, which I did not read.
- Accuracy with the post-change frames left in: not stated.
- Exact-match accuracy over the 81 combinations: not stated.

## Architecture and training (checking the earlier assumptions)

### Takeaway
- **Confirmed:** 70/20/10 split; 320×320 nozzle crop resized to 224×224; three training stages; AdamW.
- **Not confirmed:** "lr 1e-3". The paper says the starting learning rate for each stage was picked with an LR range sweep and is listed only in the SI.
- **Correction to "random":** the paper does not say the split is random.

### Cited Findings
- Backbone (Results › Model architecture): "a single shared Attention-56 network backbone… followed by four separate fully connected output heads after the flattening layer". Also: "The shared network backbone consists of three attention modules and six residual blocks and is based on the Attention-56 model." Each head has three output neurons (low, good, high). — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Loss (Methods › Training procedure): "we determine the cross-entropy loss at each of the heads and then sum these losses together before backpropagation." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Input pipeline and augmentation, in this order (Results › Dataset generation):
  1. Rotate the full image "by up to 10 degrees in either direction".
  2. Apply a "minor perspective transform… with a probability of 0.1".
  3. Crop to "a 320 × 320 pixel square region focused on the nozzle tip using the nozzle tip coordinates".
  4. Take a random square crop covering "an area between 0.9–1.0 of the 320 × 320 image" and resize it "to 224 × 224".
  5. Flip horizontally with p=0.5.
  6. Apply "colour jitter of ±10%" to brightness, contrast, hue and saturation.
  7. Normalise each channel using "each channel's pixel mean and standard deviation for all the images in the filtered dataset". These are dataset statistics, not ImageNet statistics.

  The raw capture is 1280×720 at 2.5 Hz (Methods). — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- The three stages, with 3 seeds each (Results and Methods). The best seed carries forward to the next stage.
  1. Trained on "only images of the first layers with 100% infill".
  2. Transfer learning on the full dataset.
  3. "only the final fully connected layer to each of the four heads was trained on a balanced sub-dataset containing an equal number of samples for each of the possible 81 combinations… The weights in the network backbone… were frozen."

  Epochs: "The three stages of training were trained for 50, 65 and 10 epochs, respectively." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Optimiser and schedule (Methods): "An AdamW optimiser was used during training with a reduce on plateau learning rate scheduler to decrease the learning rate by a factor of 10 when 3 epochs in a row didn't improve the loss by more than 1%." Starting learning rate: "selected at each of the 3 training stages by sweeping a range of values and selecting a learning rate with a large drop in loss [Smith 2017]. Learning rates for each of the stages can be seen in the supplementary information." The authors add: "a high learning rate led to poor attention maps". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Compute: trained in FP16 on 2× Quadro RTX 5000 with PyTorch 1.7.1. The same machine ran online inference. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Label sampling ranges (Methods): flow rate 20–200%, lateral speed 20–200%, Z offset −0.08 to 0.32 mm, hotend 180–230 °C. New values were sampled uniformly every 150 images (about 1 min). "some additional flow rates at higher levels needed to be added to the training set". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Why the authors chose attention: it is "believed that these mask branches can make the network more robust to noisy labels". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

### Inferences
- If our code uses lr=1e-3, that value comes from the repo or our own choice, not the paper. The paper's per-stage learning rates are in SI Fig. S1, which I could not read.

### Gaps
- Per-stage learning rates, weight decay and LR plots: in the SI only, not read.
- How the train/val/test split interacts with the stage-1 and stage-3 sub-datasets: not stated.

## Correction loop

### Takeaway
- Inference runs at 2.5 Hz.
- Each parameter keeps a list of its last L predictions. When one class makes up at least θmode of the list, that class is accepted as the mode. A mode of "too high" or "too low" triggers a correction.
- The correction is proportional: the mode fraction is mapped linearly from [θmode, 1] onto [Imin, 1], and that factor scales the maximum step (A+ or A−).
- After an update, the loop waits for the printer to acknowledge the command before predicting again.
- Toolpaths are split into moves of at most 1 mm during correction runs.
- The per-parameter values sit in the Fig. 3b table, an image I could not read.
- "~6 s" is the label-filtering response time. It is not a measured correction latency.

### Cited Findings
- Capture and crop (Results › Online correction): "images of the nozzle tip and material deposition are taken at 2.5 Hz and sent to a local server for inference… cropped to a 320 × 320 pixel region focused on the nozzle tip. The user needs to specify the pixel coordinates of the nozzle once". On crop size: "the best balance between accuracy and response time is seen when ~5 extrusion widths are visible on either side of the nozzle tip." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- How predictions are aggregated (same section): "These predicted parameters are stored in separate lists of different set lengths, L, for each parameter. If a particular prediction is made frequently enough that it makes up a proportion of a full list greater than or equal to the mode threshold (θmode), then a mode is found… If no mode is found, then no updates are made". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- How a correction is sized: "the proportion of the list length constituted by the mode value is used to scale the adjustment… one-dimensional linear interpolation is applied to map the range between a parameter threshold (θmode) and 1 to a new minimum (Imin) and 1. The interpolated value is then used to linearly scale the maximum update amount (A+ for parameter increases and A− for decreases)." The values "were obtained iteratively via experimentation for each parameter individually (Fig. 3b)". "The hotend list length and mode threshold are particularly conservative due to the long response time of this parameter and also the safety risk in overshooting." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Fig. 3 caption: "b Table containing θmode (mode threshold), L (sequence length), Imin (interpolation minimum), A+ (the largest increase), A− (largest decrease) for each printing parameter along with the possible levels of update amounts." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Acknowledgement gating: a Raspberry Pi issues the G-code and waits for the firmware to acknowledge it over serial. "When the server receives an acknowledgement that all updates have been executed it begins to make predictions again. Waiting for this acknowledgement of all parameter updates is crucial to stop oscillations caused by over and undershooting the target." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Toolpath splitting: moves are at most 2.5 mm in data collection and 1 mm in correction runs, "to enable significantly faster firmware response times". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Speed claim (Discussion): the system gives "an order of magnitude improvement in correction speed and response time compared to previous work". No number in seconds is given in the text. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Where the 6 s comes from (dataset filtering, not the control loop): "changes are predominantly visible within 6 s of an update being applied" — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Oscillation risk (Discussion): "Parameter oscillations can occur if the network can still see a previously bad region and overshoots its correction or upon a series of incorrect predictions". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

**Generalisation demos.** All are qualitative. None reports a success rate, accuracy or time-to-correct number in the text.

- **Same CR-20 Pro, changed setup (Fig. 4a).** The camera was "slightly rotated and translated", with a new 0.4 mm nozzle of different external geometry and an unseen single-layer sample. The single-parameter errors were corrected: "rapidly able to recover good printing parameters". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- **Unseen thermoplastics (Fig. 4b).** Four materials, including TPU and carbon-fibre-filled filament, each with random multiple bad parameters: "the network successfully updates multiple parameters". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- **Z offset fixed through flow (Fig. 4c).** In a high-Z-offset region, the network raised flow rate and lowered Z. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- **Rook, 3D part (Fig. 4d).** Bad parameters were injected halfway through the print. The uncorrected rook "dramatically failed" and the corrected one completed. Counts: 1 vs 1. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- **Spanners (Fig. 4e).** Uncorrected 3 vs corrected 3. Without correction: "one complete failure… very poor surface finish on the remaining two". With correction, all three completed. The authors caveat that "corrected prints do not match a perfectly printed part… a correction can also be applied when it is not needed". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- **Unseen printer: Lulzbot Taz 6 (Fig. 5a–c).**
  - Setup: 0.6 mm nozzle, 2.85 mm filament, Raspberry Pi Camera v1 with a different lens and position.
  - Bishop: errors injected at layer 7. The uncorrected bishop failed and the corrected one succeeded.
  - Single-layer benchmarks in white PLA were also corrected.

  — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- **Direct ink writing (Fig. 5d–e).**
  - Setup: syringe extruder on an Ender 3 Pro.
  - Materials: PDMS (0.21 mm nozzle), and mayonnaise and ketchup (0.84 mm nozzle). No hotend correction.
  - PDMS: only flow was corrected, with overshoot "due to a large build of pressure in the syringe".
  - Condiments: flow and Z were adjusted.

  — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

### Inferences
- The "response time" in any demo is not measured in the text. Our system should report its own measured time-to-correct rather than cite one from CAXTON.
- As a rough calculation from the stated rate only: the window covers L/2.5 s of frames, so L=10 would be 4 s. The real L values are in Fig. 3b.

### Gaps
- Numeric θmode, L, Imin, A+ and A− for each parameter: in the Fig. 3b image only, not read.
- End-to-end inference latency in ms: not stated.
- Measured time-to-correct: not stated.
- Correction success rates across many trials: not stated. The demos are single examples or 3-vs-3 comparisons.

## Explainability

### Takeaway
The paper uses three methods:
- the residual-attention mask outputs, shown per module;
- guided backpropagation;
- Grad-CAM, computed separately for each head and class, which gives up to 12 maps per image.

The conclusion is that the last layers focus on the most recent extrusion at the nozzle tip, whatever the parameter or class.

### Cited Findings
- Attention masks (Results, Fig. 2b): "The network appears to focus on the printed regions in the example mask output for attention module 1, and then only on the most recent extrusion for module 2. Module 3 applies the inverse to the previous, focusing on everything but the nozzle tip." The authors note the masks are "illustrative examples". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Per-head method (Results › Gradient-based visual explanations): "a method was developed to apply the techniques for each parameter separately within the whole network allowing us to produce up to 12 tailored visualisations for an input image". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Guided backpropagation finding: "similar features are shared between parameters for the same extrusion classification: separated paths for under extrusion, an outline of the current path for good extrusion, and around the nozzle for over extrusion." — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Grad-CAM, applied to every backbone layer and shown for residual blocks 1 and 6: "Earlier stages… differentiating between the deposited material and the print bed. By the last layer, the network predominantly focuses on the most recent extrusion from the nozzle irrespective of parameter or target class." The authors say the same patterns hold on DIW images (Fig. 6d). More examples are in SI Fig. S2 and Movie S3. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Discussion: the network "identifies visual features that are universal to extrusion processes, such as the shape of the extrudate". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

### Inferences
- All the explanations are qualitative, picked examples. There is no faithfulness or deletion metric, so CAXTON offers no quantitative explainability baseline for us to match.

### Gaps
- Quantitative evaluation of the saliency maps: not stated (none).

## Label lag and caveats

### Takeaway
- After each parameter update, the code waits for the printer's acknowledgement before capturing frames, then drops the first **15 images** captured. At 2.5 Hz, 15 frames is 6 s, which matches the worst-case 6 s visibility test.
- On Z offset, the paper reports two limits: a dataset biased towards high Z offset, because low values are bounded by bed contact, and small Z changes that are hard to see.

### Cited Findings
- On ack gating and the frame drop: "The first delay is mostly handled by only capturing images after an acknowledgement of the parameter update command has been received from the printer. For mechanical delay, worst-case experiments were run to determine the response time for changing each parameter from the minimum to the maximum value… changes are predominantly visible within 6 s of an update being applied, and as such, 15 images are removed post parameter updates." The same 15 frames are dropped for every parameter, including hotend. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- The authors say noise remains: "The remaining dataset contains some noisy labels due to the longer response times…". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Z bias (Results): "the Z offset can have many more values which are too high than too low because the nozzle would crash into the print bed". This bias is why stage 3 trains on balanced data. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Discussion: "More data for low Z offset values may also be beneficial as small differences in value can have a large impact on print quality… we believe the small movements in Z offset may be the primary weakness of the current dataset and improved camera focus, resolution and attention to positioning would greatly improve the next iteration". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)
- Why parameters were sampled at random rather than systematically (Methods): random sampling means the image periphery shows extrusion from a different, earlier parameter set. This "may help train the network to use local features around the nozzle tip". — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646/)

### Inferences
- The hotend responds much more slowly than flow, yet gets the same 15-frame drop. The hotend labels are probably the noisiest, which fits it being the lowest-accuracy head (78.3%). This is my inference.

### Gaps
- Separate drop windows for each parameter: not stated (one global value of 15 frames).
- Dataset: DOI 10.17863/CAM.84082. Code: github.com/cam-cambridge/caxton. Neither checked here.
