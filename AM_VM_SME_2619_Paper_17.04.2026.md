# Parameter Optimization for Additive Manufacturing of

> Converted from `AM_VM_SME 2619_Paper_17.04.2026.pdf`. The original page structure is preserved with page headings.

> **Note:** Figure images are extracted separately and referenced from this Markdown file so the visual material can be retained when the folder is moved together.


---

## Page 1


Parameter Optimization for Additive Manufacturing of
Lightweight Components in Aerospace/Automotive
Applications.

Vinod Kumar V Meti1*, Vaibhav Vinod Dhulla1, Krish Ketan Patel1, Kamalaksh Dessai1, Vijaykumar S. Jatti2,
Sandeep C Dhaduti3, Anil M Kabbur4 and IG Siddhalingeshwar3
1 Department of Automation and Robotics, KLE Technological University, Hubballi-580031, India.
2 Symbiosis Skills and Professional University, Kiwale, Pune, Maharashtra, India.
3 Department of Mechanical Engineering, KLE Technological University, Hubballi-580031, India
4 Electronics and Communication Department, Indian Institute of Information Technology, Dharwad, India.

Abstract. Additive Manufacturing (AM), commonly referred to as 3D printing, is revolutionizing the
aerospace and automotive industries by enabling the production of intricate and lightweight components
from
digital
files,
and
further
decreasing
waste
and production time
compared to
conventional_methods.Although Fused Deposition Modelling (FDM) is a popular AM technique due
to its accessibility and inexpensive cost, its output quality is highly dependent on variables such as lay
er height, print speed, bed temperature, and nozzle temperature. This study combines the industrialgrade Aion 500 printer with real-time fault detection and parameter adjustment. After printing under
various conditions, a representative aerospace part was designed and printed in solid and topology
optimized to assess accuracy, strength, material efficiency, and overall geometrical refinement. A
YOLOv8 deep learning model was trained for defect recognition using a bespoke dataset, highdefinition webcams, and edge computing modules to record still images. The findings demonstrated a
34% decrease in geometric deviation, a 27% improvement in surface quality, and a 40% improvement
in dimensional consistency. In addition, YOLOv8 real-time monitoring achieved 91.3% accuracy at 20
frames per second. This study shows that combining AI-based monitoring with parameter optimization
improves the reliability of FDM and pushes the process closer to intelligent, defect-aware
manufacturing. At this stage, the system focuses on real-time monitoring with simulated corrective
feedback rather than fully autonomous control. However, the framework sets a clear foundation for
future closed-loop implementations where the printer can adjust parameters automatically during the
build.
1. Introduction
1.1 Background and Motivation
From a prototyping technique to a valid way to produce end-use parts for a variety of high-tech industries, additive
manufacturing (AM) has experienced a revolutionary evolution.  Engineers can create complex geometries using its
fundamental idea of layer-wise fabrication from digital models, which is otherwise impossible with conventional
subtractive or formative processes.  In industries like aerospace and automotive, where reducing weight without
sacrificing structural performance is essential for fuel economy, payload capacity, and overall system performance,
this transformation has proven particularly helpful.
  Nevertheless, despite these advantages, FDM is still not widely used in safety-critical applications.  Its
vulnerability to print flaws, inconsistent output quality, and absence of reliable in-process monitoring systems are the
main causes of this. Manufacturing standards are strict in the automotive and aerospace industries.  High levels of

1* Corresponding author: vinod_meti@kletech.ac.in


---

## Page 2


production repeatability and traceability are required by certification frameworks like ISO 9001 (general quality
assurance) and AS9100 (aerospace quality management).  Consequently, a component may become unfit for service
due to even slight changes in surface finish or part geometry.  Furthermore, material waste, longer lead times, and
safety issues may result from a failure to identify and fix flaws during the construction process.
According to recent studies, intelligent monitoring in conjunction with process parameter optimization can greatly
improve FDM's repeatability and dependability.  Though most implementations are either offline or only concentrate
on defect detection without integrating into process control loops, the integration of computer vision and machine
learning into additive manufacturing workflows has created opportunities for real-time quality assessment.
Despite notable progress in combining machine learning and additive manufacturing, the majority of current
research treats these fields separately.  Few studies, especially on industrial-grade platforms, provide a cohesive
system that integrates adaptive process control, real-time defect detection, and smart component design.  Furthermore,
even though object detection algorithms like YOLOv4 and YOLOv5 have been used in previous research, their
application was frequently restricted to post-processing, which rendered them useless for live intervention in the event
of print failures.  YOLOv8, the most recent advancement in object detection, offers prospects for increased speed and
accuracy in anomaly detection.  Its use in real-world FDM settings, particularly on hardware such as the Aion 500,
has not, however, been fully explored.

Fig 1.1: The circular workflow of 3D printing with Polylactic Acid (PLA), from its natural source to the final product and its
applications.
1.2 Problem Statement
Despite notable progress in combining machine learning and additive manufacturing, the majority of current research
treats these fields separately.  Few studies, especially on industrial-grade platforms, provide a cohesive system that
integrates adaptive process control, real-time defect detection, and smart component design.  Furthermore, even
though object detection algorithms like YOLOv4 and YOLOv5 have been used in previous research, their application
was frequently restricted to post-processing, which rendered them useless for live intervention in the event of print
failures.  YOLOv8, the most recent advancement in object detection, offers prospects for increased speed and accuracy
in anomaly detection.  Its use in real-world FDM settings, particularly on hardware such as the Aion 500, has not,
however, been fully explored.
Furthermore, topology optimization—which has the potential to significantly lower material consumption while
preserving part strength—is frequently researched in simulation without validation through actual printing.
 By creating a comprehensive framework that consists of (a) topology-optimized lightweight part design, (b)
process parameter tuning, and (c) real-time computer vision-based defect detection using YOLOv8, this study fills
these gaps.  The Aion 500, a high-precision FDM system, is used to validate the implementation in conditions relevant
to the industry.


### Figures / Images on this page


![Page 2 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_02_image_01.png)


---

## Page 3


Fig 1.2: Experimental Setup with 3D Printer and Image Acquisition for Process Observation.
1.3 Research Objectives
The main objective of this research is to improve FDM's efficiency and dependability for producing lightweight,
aerospace-grade parts.  Data-driven, computational, and experimental approaches will all be used to accomplish this.
The particular goals are:
1. To compare the material consumption and mechanical behavior of aerospace-inspired components designed and
manufactured in both standard and topology-optimized formats.
2. To determine and adjust crucial process variables that affect surface integrity and dimensional accuracy, such as
print speed, bed temperature, nozzle temperature, and flow rate.
3. To create a high-definition camera system for real-time visual monitoring and identify the best location for the
greatest visibility of defects.
4. To train a YOLOv8-based classification model, annotate and enhance a dataset of FDM defects, such as stringing,
under-extrusion, warping, and layer shifting.
5. To install an inexpensive edge computing module that can capture and process images in parallel, allowing for
long-term monitoring without requiring a lot of processing power.
6. To compare defect rates, surface finish, print accuracy, and repeatability between baseline and optimized runs in
order to assess the efficacy of the integrated system.
1.4 Significance of the Study
This study suggests a scalable, economical, and useful method for FDM quality assurance.  The study shows how
intelligent systems can improve manufacturing accuracy and sustainability by validating a topology optimization
workflow in a real-world setting and combining it with live visual monitoring.  The knowledge gathered from this
work can be applied to any field that needs high-reliability polymer-based AM, not just the automotive and aerospace


### Figures / Images on this page


![Page 3 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_03_image_01.png)


---

## Page 4


industries. This research, in contrast to many theoretical studies, focuses on practical implementation, producing a
methodology that industry R&D labs, startups, and academic institutions can use without incurring prohibitive costs.
It becomes repeatable, adaptable, and forward-compatible with future machine learning architectures when real-time
monitoring is incorporated using open-source tools like YOLOv8 and Roboflow.
1.5 Structure of the Paper
The previous attempts at defect detection, monitoring, and optimization within FDM are covered in Section 2:
Literature Review, along with the current gaps that this study seeks to fill.
 The experimental setup, software tools, camera configurations, preparation of the defect dataset, and the YOLOv8
training pipeline are described in Section 3: Methodology.
 Section 4: Results and Discussion examines the efficacy of the suggested system and provides quantitative gains
in print quality.
 Section 5: Final Thoughts and Prospects Key findings are outlined in the scope, along with recommendations for
future advancements like closed-loop control and integration with predictive modeling tools.

Fig 1.3: This figure visually outlines the entire research framework, illustrating the systematic steps from conceptualization and
material selection through to the printing, monitoring, and final evaluation stages.
2. Literature Survey
The rapid evolution of Additive Manufacturing (AM) from a prototyping tool to a full-fledged production
methodology has created a pressing need for robust, real-time monitoring and autonomous quality control. In
particular, integrating Artificial Intelligence (AI), especially deep learning and machine vision, has emerged as a focal
point for researchers aiming to tackle process inconsistencies and defects, especially within Fused Deposition
Modeling (FDM) and other AM variants. Several studies have contributed meaningfully to this frontier, demonstrating
both the potential and challenges of embedding intelligent monitoring into AM workflows.
Strong, real-time monitoring and independent quality control are urgently needed as a result of Additive
Manufacturing's (AM) quick transition from a prototyping tool to a full-fledged production methodology. Researchers
are focusing on integrating Artificial Intelligence (AI), particularly deep learning and machine vision, to address
process defects and inconsistencies, particularly in Fused Deposition Modeling (FDM) and other AM variants.
Numerous studies have made significant contributions to this field, highlighting the advantages and disadvantages of
integrating intelligent monitoring into AM processes.
 Xu et al. [1] made a noteworthy contribution in this area by creating a lightweight object detection framework
with YOLOv4-tiny that is designed for real-time FDM process monitoring. The deployment of this work on
inexpensive, edge computing platforms like the Raspberry Pi and NVIDIA Jetson Nano is what gives it a particularly
significant impact.  By avoiding the need for expensive GPUs or cloud infrastructure, this option makes quality control
more accessible for distributed manufacturing settings and smaller labs.  Filament tangling, under-extrusion, stringing,
and warping-induced dimensional deviations are just a few of the many FDM-specific anomalies that the model was
trained to identify.
 With a mean Average Precision (mAP) of over 84% and a throughput of 17 frames per second at 640x480
resolution, the system demonstrated that it can function well under practical limitations without compromising
detection accuracy.  This study demonstrated how lightweight AI can democratize quality assurance by setting a solid
precedent for localized, real-time defect identification in AM, particularly in printing environments that are
decentralized or have limited resources.  It also established a standard for the upcoming generation of embedded


### Figures / Images on this page


![Page 4 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_04_image_01.png)


---

## Page 5


monitoring systems by confirming that improving print quality does not always require a large amount of infrastructure
or processing power.
 Although FDM is frequently the main focus, other specialized AM processes—like ceramic 3D printing—
introduce special difficulties that call for customized solutions.  Zhou et al.'s work [2] specifically addressed this issue
by proposing a dual-camera vision-based system that is specifically made to assess the surface quality of ceramic
components.  Ceramics have very different material characteristics and failure modes than metals or polymers, such
as uneven glaze deposition, moisture-induced sagging, and toolpath anomaly-induced micro-ridge formation. The
authors created a setup that captures both top-down and angled side views in recognition of the limitations of singleview inspection. This greatly improves defect visibility and enriches the visual dataset.
 Their approach depended on a precisely calibrated Convolutional Neural Network (CNN) that classified and
segmented these subtle flaws.  Thanks in part to extensive preprocessing techniques like illumination control, image
normalization, and contrast enhancement—all of which are particularly important given the reflective and optically
inconsistent nature of unfired ceramics—the system impressively achieved over 90% classification accuracy.  This
study supports the notion that there is no one-size-fits-all solution for all AM domains and emphasizes the significance
of process-specific monitoring techniques.  Adaptive frameworks that are sensitive to the peculiarities of processes
and material behaviors are required instead. Building on this idea, Chung et al. [3] used DenseNet, a CNN architecture
known for its feature reuse and parameter efficiency, to improve defect detection in ceramics.  Their work concentrated
on finding structural cracks and microscopic voids, which are flaws that can seriously jeopardize part integrity but are
frequently invisible to the human eye.  Over 3000 high-resolution annotated photos covering a variety of problems,
such as inter-layer delamination, pinholes, and unwanted surface textures, were used to train the model.
 Their use of cutting-edge data augmentation techniques was what made their strategy unique.  They mimicked
real-world inconsistencies in image capture by applying controlled Gaussian blur and simulating changes in lighting.
These improvements greatly increased the model's resilience, especially when it came to generalizing across different
printer behaviors and environmental conditions. Furthermore, transfer learning from ImageNet weights reduced the
need for computationally costly, extensive training from scratch while speeding up training and increasing accuracy.
 In terms of metrics like recall and F1-score, the DenseNet-based system performed better, particularly when
handling small-scale, low-contrast defects.  Crucially, their model's inference phase was still sufficiently light to
operate without specialized GPUs, making it both potent and affordable.
These studies collectively demonstrate that intelligent defect detection in AM is not only possible but also
becoming more and more useful, even in environments with limitations.  The focus throughout the literature is on
real-time adaptability, material-specific customization, and deployment viability, whether through high-capacity
DenseNets, dual-camera systems, or lightweight YOLO architectures.  As AM applications grow in the automotive,
biomedical, and aerospace industries, the role of such smart monitoring frameworks becomes even more critical—
ensuring not just part quality, but also process repeatability, compliance, and long-term reliability.

Fig 2.1: The working principle of FDM printer [1].


### Figures / Images on this page


![Page 5 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_05_image_01.png)


---

## Page 6


Garfo et al. [4] extended the field of polymer-based FDM monitoring by thoroughly examining the real-time
classification of surface defects using MobileNet-SSD, a powerful yet lightweight deep learning architecture designed
for speed and edge deployment.  The goal of their study was to find frequently seen but frequently disregarded flaws
that have a substantial impact on the functional and aesthetic quality of FDM prints.  These included surface
delamination brought on by inadequate layer adhesion, inter-filament gaps that impair part strength and surface finish,
inconsistent extrusion lines that affect dimensional precision, and stringing—thin plastic filaments that inadvertently
connect parts.
 Their focus on resource-constrained hardware deployment, especially with the Raspberry Pi 3, is what
distinguishes their methodology.   The testbed for assessing model performance in practical, cost-conscious situations
was a low-cost edge computing platform. By achieving a mean Average Precision (mAP) of 88% at 15 frames per
second (FPS) for 300×300 pixel inputs, MobileNet-SSD clearly demonstrated its balance between computational
efficiency and classification capability, outperforming its peers when benchmarked against other compact CNN
models.
 One important finding from their research was that image resolution has a non-linear effect on detection
performance.  Higher resolutions did increase sensitivity to minute flaws, but they also increased computational load
and latency, which made real-time responsiveness less reliable. Applications for mobile or the FDM monitoring are
also available. In educational, hobbyist, and small business settings, where cost and computational constraints
frequently impede the adoption of intelligent monitoring systems, Garfo et al.'s work offers an approachable, scalable
template for incorporating defect detection into entry-level desktop printers. When compared to other compact CNN
models, MobileNet-SSD outperformed its peers with a mean Average Precision (mAP) of 88% at 15 frames per second
(FPS) for 300×300 pixel inputs, demonstrating a clear balance between computational efficiency and classification
capability.
  The fact that image resolution has a non-linear impact on detection performance was one of their key findings.
Although sensitivity to subtle defects was enhanced by higher resolutions, real-time responsiveness was compromised
by increased computational load and latency.   There are also applications for mobile FDM monitoring.   The work by
Garfo et al. provides a scalable, approachable template for integrating defect detection into entry-level desktop printers
in educational, hobbyist, and small business settings, where financial and computational limitations typically prevent
the adoption of intelligent monitoring systems.

Fig 2.2: This image displays the real-time operational interface of the industrial 3D printer, highlighting the critical data and precise
controls available during a live printing job.

Additionally, the study provided a thorough analysis of how dataset diversity affects model robustness.  Verana et
al., showed a notable increase in generalization capacity by varying the lighting, defect severities, and background
textures during training.  The significance of environment-aware training data was highlighted by their ensemble
model's consistent high accuracy on unseen, real-world samples.  In situations where false positives or
misclassifications could result in expensive material waste or production downtime, this work demonstrates how
ensemble learning can act as a trustworthy "second opinion" system, supporting defect detection.


### Figures / Images on this page


![Page 6 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_06_image_01.png)


---

## Page 7


Ramos et al. [6] developed a novel technique for defect detection in fused filament fabrication (FFF) using infrared
(IR) thermography, whereas the majority of earlier work relied on optical RGB imaging.
IR imaging provides a more thorough examination of thermal gradients and subsurface conditions than RGB
systems, which mainly capture surface details.  In order to identify early indicators of failures like overheating zones,
cold patches, and irregular cooling patterns, Ramos et al.'s system used a regression-based CNN that was trained to
predict temperature deviations across layers.
 The system predicted failures like warping and delamination up to five layers before visual symptoms appeared,
with a mean absolute error of ±3°C in thermal prediction.  With this predictive capability, AM monitoring has
undergone a significant change from reactive inspection to proactive process intervention.  Their findings also
demonstrated a robust relationship between mechanical strength deterioration and thermal anomalies, confirming the
use of thermal imaging as a diagnostic and prognostic method.
Additionally, the study established a solid basis for closed-loop thermal control systems, which allow for real-time
adjustments of parameters like fan speed or nozzle temperature to stop the formation of defects.
 Paul et al. [7] extended this multi-modal viewpoint by presenting an advanced sensor fusion framework that
integrated extrusion torque, acoustic emission, and thermal imaging data to produce a comprehensive picture of the
FDM process.  Detecting both visual and non-visual abnormalities was the goal of this tri-modal setup.  Acoustic
sensors tracked stress waves suggestive of microcracks or layer separation, torque sensors gave feedback on nozzle
pressure and flow consistency, and thermal cameras recorded spatiotemporal heat distributions.
Shallow neural networks were used for the initial feature extraction of each data stream, specifically designed to
extract pertinent indicators like torque fluctuations, frequency spikes, and thermal variance statistics.  A Gradient
Boosting Decision Tree (GBDT) was then used to fuse these features, greatly increasing detection accuracy by 12%
compared to single-sensor systems.
 Crucially, their system underwent extensive validation in real-world industrial settings, such as temperature
variations and mechanical vibrations, which are known to impair sensor performance.  However, the model showed
remarkable resilience, proving that reliable, field-deployable AM monitoring systems are feasible.  This work lays the
groundwork for intelligent, self-correcting AM platforms that function dependably in uncertain production
environments and supports the growing consensus that multi-modal sensing is crucial for capturing the entire range
of process behavior.
Beyond additive manufacturing, the increasing success of AI-based defect detection has spread to related
production techniques, providing insightful information that can be applied elsewhere.  The work of Kim et al. [9],
who used the YOLOv5 object detection framework to monitor surface defects in polymer injection molding in real
time, is a powerful example.  Even though injection molding is a formative process rather than an additive one, it
shares many of the same issues with AM, especially when it comes to guaranteeing surface finish quality and
identifying minute flaws that could jeopardize part functionality.
 This is particularly difficult in areas with curved or glossy surfaces, where consistent light scattering, strong
reflections, and specular glare make visual inspection difficult.
.  The researchers suggested a novel improvement to YOLOv5 in the form of a reflection-aware loss function in
order to address these optical issues.  This custom loss function was specifically designed to penalize prediction errors
occurring in glare-heavy regions, improving the model’s ability to distinguish actual defects from visual noise.
 The improved YOLOv5 model performed exceptionally well, detecting defects in high-speed video feeds from
live production lines with an accuracy of over 95%.  Its ability to maintain an inference speed above 30 frames per
second further validates its appropriateness for in-line quality assurance systems where low latency and high
throughput are essential.  The study also highlighted how robust, real-time monitoring can be made possible even in
dynamic and difficult lighting conditions by combining model-level improvements with image preprocessing methods
like adaptive thresholding and glare filtering.
Although injection molding was the main application, the methods created to manage optical complexity are highly
applicable to resin-based AM technologies like Material Jetting, DLP, and SLA.  These procedures frequently involve
surfaces that are metallic, translucent, or reflective, where traditional defect detection models fall short.  Thus, the
work of Kim et al., provides a transferable model for AI monitoring that is aware of optics on a variety of AM
platforms.
 Zhu et al. [10] presented a novel methodology that closely integrates real-time defect prediction with generative
design and topology optimization in order to provide manufacturing feedback in a more design-integrated manner.
Their study presents a closed-loop framework in which the objective functions of topology optimization algorithms
used in the design of aerospace components are directly factored in regions that are prone to defects, as determined
by AI models during the printing process.


---

## Page 8


Areas that are commonly prone to flaws like warping, porosity, delamination, or fusion failure are either penalized
or structurally reinforced during design generation in this process-aware optimization loop.  The end product is a
component that is naturally more manufacturable and has fewer defects, in addition to meeting strict structural
performance targets (such as stiffness, strength, and fatigue life).
The efficacy of this approach was validated through experimentation.  When compared to conventional,
manufacturing-agnostic optimization techniques, components designed with this integrated framework demonstrated
a 12% reduction in overall weight without compromising fatigue performance or structural integrity.  This illustrates
how computational design workflows can be actively informed by real-time print data, resulting in smarter, more
robust parts right from the start.  A major advancement in design-for-manufacturability and reliability—a paradigm
that is becoming more and more crucial for high-value industries like aerospace—is made possible by the research's
successful integration of digital design tools with the physical process.
The foundational work in effective neural network design is the driving force behind many of the lightweight AI
systems used in AM monitoring today.  The MobileNet architecture, which Howard et al. [11] presented in their
seminal paper, fundamentally altered the way Convolutional Neural Networks (CNNs) were implemented on devices
with constrained processing power.  The use of depthwise separable convolutions, which split a standard convolution
into two smaller, computationally efficient steps—a depthwise convolution, which applies one filter per input channel,
and a pointwise convolution, which fuses the results across channels—is the core of MobileNet's innovation.
 An optimal trade-off for on-device inference, this architectural restructuring results in 8–9× reductions in both
model size and computation (MACs) while maintaining competitive accuracy.
 Additionally, MobileNet added tunable hyperparameters like the width multiplier and resolution multiplier, which
allowed researchers to modify the model's complexity according to deployment limitations like memory availability,
power consumption, or latency.
 By enabling real-time computer vision on edge devices, mobile platforms, and embedded controllers, this research
paved the way for a new era of on-device AI.  Since then, MobileNet's fundamental concepts have been improved
upon and expanded in a variety of lightweight models, many of which have been used for AM quality monitoring,
where low latency and energy efficiency are essential for in-process control.  The broad use of the architecture
highlights how important it is to enable intelligent AM monitoring, as well as make it feasible and scalable.
Accurately identifying and mitigating critical defect morphologies in real time is a major challenge in additive
manufacturing (AM), especially in fused deposition modeling (FDM).  Of these, warping continues to be one of the
most enduring and functionally harmful problems.  Warping, which is brought on by uneven cooling and the
subsequent buildup of thermal stress within the material, usually appears as the lifting or deformation of part edges
from the build platform.  A multi-sensor fusion method designed for the real-time detection and measurement of
warping severity during the print process was put forth by Jin et al. [12] in order to address this issue.
 Their approach made use of an adaptable set of sensors, each selected for its unique set of capabilities.
Stereoscopic camera systems and structured light captured discernible dimensional deviations and changes.
For the purpose of locating areas of thermal instability, thermal imaging produced a dynamic map of temperature
gradients throughout the part and the build plate.  Crucially, they also added Inertial Measurement Units (IMUs) to
the sensor stack, which allowed for the detection of signals that may precede or accompany warp initiation, even
before visual deformation is noticeable, such as micro-vibrations, printbed shifts, or minute part tilting.
 A robust estimator of warping amplitude with a precision of ±0.15 mm was produced by cleverly fusing the data
streams using sophisticated signal processing and predictive modeling techniques.  In practical applications, where
early detection permits interventions like changing fan speeds or bed temperatures, this degree of accuracy is crucial.
Furthermore, the outputs of their system feed straight into closed-loop control systems and are not only diagnostic but
also actionable.
By dynamically adjusting variables like cooling rate, enclosure temperature, infill density, or print speed, these
systems can reduce warping before it spreads and enhance print quality and dimensional fidelity in general.  The work
of Jin et al. offers a model for sensor-integrated FDM systems that can print in a flexible, defect-resistant manner.  Xie
et al. [13] carried out a thorough benchmarking study of machine learning approaches across a variety of typical AM
challenges in an attempt to standardize and elucidate the expanding corpus of research in AI applications within AM.
Up to eleven machine learning algorithms—including deep learning architectures like CNNs and RNNs, ensemble
learners like Random Forests and Gradient Boosting, and traditional supervised classifiers like SVMs and Decision
Trees—were thoroughly compared in their study using a variety of AM-relevant tasks.
Defect detection, process parameter prediction, property estimation from sensor data, and real-time monitoring
interpretation were among these tasks.  Several established metrics, including accuracy, precision, recall, F1-score,
inference time, and robustness to data noise, were used to assess the models. These metrics were applied to a variety


---

## Page 9


of datasets, including FDM, SLM, and ceramic printing, as well as different materials, such as polymers, metals, and
composites.
 Their study's consistent superiority of transfer learning techniques—where models pre-trained on sizable, generalpurpose datasets (like ImageNet) were refined with domain-specific AM data—was one of its most notable findings.
When labeled AM datasets were scarce, as is frequently the case in specialized industrial or academic setups, this
method performed noticeably better than models trained from scratch. Additionally, Xie et al. emphasized persistent
issues in AM-focused AI research, such as the imbalance of datasets, the absence of standardized datasets, and the
challenge of transferring models between AM modalities (e.g. from SLM to FDM).  Their benchmarking work offers
a crucial roadmap for ML deployment in AM by outlining performance trade-offs and providing specific model
selection recommendations, swiftly integrating AI into practical additive workflows.
 Yi Chia et al. [14] investigated clever methods for real-time process optimization in Selective Laser Melting
(SLM) and Direct Energy Deposition (DED), focusing on metal AM, where process complexity and material cost are
much higher.  These methods, which depend on the localized melting of metal powders, are vulnerable to flaws like
residual stress-induced cracking, porosity, keyholing, and incomplete fusion. All of which critically affect the
mechanical performance and reliability of the final components.
Additionally, Xie et al., emphasized persistent issues in AM-focused AI research, such as the imbalance of datasets,
the absence of standardized datasets, and the challenge of transferring models between AM modalities (e.g. from SLM
to FDM).  Their benchmarking work offers a crucial roadmap for ML deployment in AM by outlining performance
trade-offs and providing specific model selection recommendations, swiftly integrating AI into practical additive
workflows.
 Their work used a multi-modal monitoring setup to address this, mainly consisting of thermal sensors such as
pyrometers and infrared cameras (for real-time temperature profiling) and high-speed coaxial cameras (for melt pool
imaging).  Shape, brightness, and thermal stability—all of which have a strong correlation with the likelihood of
defects—were among the rich data that these sensors recorded that showed the behavior of melt pools.
 This sensor data was incorporated into a framework for Bayesian Optimization, a sample-efficient search
algorithm that is perfect for optimizing functions that are expensive to evaluate, such as full AM builds.  In order to
predict part quality, sensor-informed surrogate models were used to iteratively adjust parameters like laser power,
scan speed, hatch spacing, powder feed rate, and layer thickness based on melt pool behavior.  Post-build CT scans
for mechanical testing, microstructural examination, and porosity analysis were used for experimental validation.
 The method greatly decreased defect rates, improved surface finish, and increased consistency across builds,
according to the results.
 The study's primary contribution is its illustration of how real-time, AI-driven decision-making can be utilized to
actively direct and monitor the metallic AM process, advancing zero-defect manufacturing in high-value industries
like biomedical implants, automotive, and aerospace.
To further support the increasing usefulness of lightweight AI models in accessible, real-world additive
manufacturing (AM) applications, Xu et al. [15] demonstrated a targeted and extremely useful implementation of
YOLOv4-tiny for real-time defect monitoring on a consumer-grade FDM printer, specifically the Creality CR-6 SE.
The CR-6 SE is a popular platform for democratizing AI-powered quality control because, in contrast to industrialgrade systems, it is utilized by educators, hobbyists, and small-scale design labs.
 By adapting the AI system to operate efficiently on less expensive hardware and within the limitations of costeffective configurations, this study builds upon previous foundational work by the same team.  It offers thorough
explanations of the implementation techniques and technical challenges required to convert sophisticated vision
systems to a non-industrial printer.  The main subjects covered are data acquisition protocols tailored to the CR-6 SE's
operating behavior and materials, such as PLA and PETG, lighting normalization techniques (to deal with irregular
ambient illumination), and camera placement optimization (to account for the printer's unique extruder path).
To identify flaws typical of this configuration, including stringing, warping, layer shifting, and first-layer adhesion
failure, the YOLOv4-tiny model was refined.  Experimental evaluations showed strong performance, with high mean
Average Precision (mAP) across all defect classes and real-time inference at realistic frame rates.  By demonstrating
that complex, deep learning-based defect detection can be successfully deployed on readily available hardware, this
work makes a substantial contribution to the field and promotes the wider use of intelligent AM monitoring systems
in low-resource settings.
The invention focuses on a persistent problem in AM defect detection: accurately detecting tiny, visually
imperceptible, or sparsely distributed flaws that traditional convolutional layers frequently overlook because of their
small receptive fields or low localization sensitivity.
 A solution is offered by Coordinate Attention, which uses a novel technique to encode both precise positional
information and long-range spatial dependencies.  It captures directional feature maps along the image's height and


---

## Page 10


width by dividing the global pooling process into two one-dimensional operations.  This improves the network's ability
to identify "what" needs attention and "where" it is present in the input image, which is essential for identifying finegrained surface flaws.
With just a few extra parameters, the addition of Coordinate Attention to YOLOv5-s led to notable mAP gains,
especially in classes with micro-defects or edge inconsistencies.  This innovation is perfect for real-time, embedded
AM monitoring scenarios where computational resources are constrained, but performance cannot be sacrificed
because it provides a convincing solution to the trade-off between detection sensitivity and model lightness.
The GUI adds real-time annotations, such as bounding boxes, defect class labels (such as "under-extrusion,"
"warping"), and confidence scores, to live video streams from a printer-mounted camera.  In addition to visualization,
the interface facilitates useful functions such as automatic defect logging, video snapshot capture, real-time alert
generation, and mid-process model and camera parameter adjustment.  This system supports human-in-the-loop
control, greatly improves operator awareness, and makes it easier to create annotated datasets for retraining in the
future.  In order to convert raw AI predictions into useful, actionable insights and improve operator trust, usability,
and decision-making in AM environments, Hu et al.'s work demonstrates how important good interface design is.
 Multi-material 3D printing, which fabricates individual components from several different materials, further
increases the technical complexity of additive manufacturing.
In a seminal review that appeared in Advanced Materials, MacDonald et al. [8] thoroughly examined this.  The
study describes the enormous functional potential of multi-material additive manufacturing (AM), which includes the
creation of bio-integrated implants, gradient composites, and aerospace parts with integrated features like
electromagnetic shielding and thermal control.
 Nonetheless, the authors stress that material heterogeneity creates significant monitoring difficulties.  Applying a
one-size-fits-all sensor configuration or defect detection pipeline is challenging because different materials have
different mechanical, optical, and thermal characteristics.  For example, when examining a nearby matte polymer,
imaging parameters tailored for a reflective metal may result in saturation.  Likewise, critical phase transitions in one
material may be obscured by thermal feedback loops that are adjusted for its cooling profile.
MacDonald et al., propose advanced sensor fusion as a solution to this problem, integrating thermal, acoustic,
visual, and even hyperspectral data to create a more comprehensive understanding of the process.  Additionally, they
emphasize the significance of adaptive control systems, which dynamically modify process parameters in real time,
such as print speed or laser power, depending on the material and its environment.  Especially in safety-critical
applications, this strategy is essential for guaranteeing inter-material adhesion, reducing the buildup of thermal stress,
and accomplishing dependable multi-material integration.
 AM is also having a significant impact on the long-standing design imperative of lightweighting in aerospace
applications.  L. Zhu et al. [9] investigated how AM-enabled design techniques, specifically lattice structures, topology
optimization, and generative design, can be used to significantly lower component weight without sacrificing
functionality.
 Their work demonstrates how additive manufacturing (AM) eliminates the geometric limitations of conventional
manufacturing, allowing for designs with intricate internal architectures like organic geometries or biomimetic lattices.
They stress that superior strength-to-weight ratios can be attained by employing topology-optimized and latticereinforced designs that are made with high-specific-strength materials such as Ti-6Al-4V, AlSi10Mg, and advanced
polymer composites. These designs frequently include multifunctional elements like modular assembly features, shock
dampening, or cooling channels.
The crucial significance of design-process-material coupling is also emphasized by Zhu et al., who emphasize that
geometry, material behavior, and AM process parameters interact to produce successful lightweight designs.  The
study combines experimental testing, such as fatigue life, dimensional stability, and mechanical strength evaluations,
with Finite Element Analysis (FEA) to validate these designs and confirm their suitability for aerospace deployment.
 Lastly, Kim et al. [5] expanded defect detection models initially created for 3D printing into the field of injection
molding, a pillar of high-volume manufacturing, to illustrate the cross-domain applicability of AM-based AI
techniques.  Based on CNNs and YOLO variations, their system was able to precisely identify common injection
molding flaws from post-molding camera images, including sink marks, short shots, flash, and weld lines.
The AI-powered method proved easier to scale, required less calibration, and was more resilient to changes in
material and lighting than rule-based machine vision systems.  The system, when integrated into fully automated
quality control (AQC) pipelines, decreased the need for manual inspection, improved yield, and shortened feedback
cycles. It also provided a model for the transfer of AI-based QA systems between conventional and contemporary
manufacturing paradigms.  This study provides compelling evidence of the adaptability and universality of intelligent
inspection frameworks, as well as the ways in which AM-fine-tuned concepts can revolutionize larger manufacturing
environments.


---

## Page 11


3. Methodology
A structured four-phase methodology was used to thoroughly assess how different print parameters and real-time
defect detection affected the overall quality of Fused Deposition Modeling (FDM) outputs.  Component design and
topology optimization, experimental setup with methodical print parameter variation, image acquisition and intelligent
defect detection, post-process analysis, and comparative data evaluation were all included in this.
 Using the Aion 500 industrial-grade FDM printer, high-resolution imaging, statistical tools, and AI-assisted
monitoring, each phase was carried out through practical experimentation.  Both qualitative and quantitative metrics
were accurately recorded thanks to the combination of intelligent analysis and physical experimentation.
3.1 Component Design and Topology Optimization
A structurally intricate mounting bracket was selected for fabrication in order to replicate a real-world use case typical
of aerospace applications.  This component's complex internal voids, thickness gradients, and overhanging features
were perfect for testing quality sensitivity and manufacturability in a variety of print conditions. Two design iterations
were created using SolidWorks: The baseline design is a standard solid-bracket geometry that is exported as a highresolution STL file.
Optimized Design: A variation with a topology optimized by applying a fixed loading condition of 10 N at the
cantilevered end, created with SolidWorks Simulation.  To evaluate the effects of lightweighting, two material
reduction targets—40% and 60%—were investigated.
Stiffness and load-bearing capacity were maintained while non-critical material was eliminated during the
optimization process.  To guarantee printability, voids and thin walls added during topology optimization were
meticulously cleaned up.  To maintain design accuracy, a 0.1 mm surface deviation tolerance was applied when
creating all STL files.  The following standard slicing parameters were then used when processing these files in
Ultimaker Cura 5.4:
 0.2 mm is the layer height; 50 mm/s is the print speed; 210 °C is the nozzle temperature; and 60 °C is the bed
temperature.
3.2 Parameter Matrix and Experimental Configuration
3.2.1 Setting Up and Adjusting the Printer
The Aion 500 was used to print all test specimens because of its precise thermal control (±1 °C) and dependable
extrusion system, which are essential for reducing variations in material flow and dimensional consistency.  A rigorous
calibration procedure was followed before starting any builds:
● Nozzle Alignment Test: A digital caliper with a resolution of ±0.01 mm was used to print and measure a 20 mm
calibration cube along the X/Y axes.  Any misalignments larger than 0.05 mm were fixed.
 ● Extrusion Multiplier Calibration: To adjust extrusion parameters, a 100 mm single-wall tube was printed.  Cura's
multiplier (1.00 to 1.05 range) was adjusted to guarantee an accuracy of 0.45 mm ±0.02 mm for wall thickness.
Error propagation throughout the 90-print experimental matrix was reduced by this calibration.
3.2.2 Design of Parameter Matrix
Because of its lower experimental load and statistical efficiency, a Box-Behnken Design (BBD) was chosen.  Three
levels of analysis were conducted on each of the following three process parameters:

Parameter
Level 1 Level 2 Level 3
Nozzle Temperature (C) 200
210
220
Print Speed (mm/s)
40
50
60
Layer Height (mm)
0.16
0.20
0.24


---

## Page 12


For every part type, the BBD generated 15 distinct print settings (baseline and optimized).  A total of 90 prints
were produced by repeating each setting three times.  Other slicer parameters, like
● Retraction: 5 mm at 40 mm/s, can be used to lessen variability.
● Cooling fan: 50% was maintained constant throughout all trials starting with Layer 2.
3.2.3 Measurement Points and Test Artifacts
For quantitative assessment, standard test artifacts were created: Surface Roughness Blocks: Five locations per sample
were used to record Ra (μm) values using a contact stylus profilometer to evaluate 50 × 50 × 5 mm coupons.
3.3 Acquiring Images in Real Time and Identifying Defects
3.3.1 Configuring Visual Monitoring
On a vibration-isolated articulated arm, a Logitech C920 webcam with 1080p and 30 frames per second was fixedly
positioned.  In order to minimize geometric distortion and guarantee complete coverage of the XY workspace, the
camera was positioned 300 mm away from the build plate.
 Diffused white LED lighting was used for illumination, especially around reflective surfaces and overhangs, to
remove harsh shadows and glare.  For accurate frame-based defect annotation, this constant lighting was essential.
3.3.2 Building and Annotating Datasets
The webcam captured full-length video during each print, which was subsequently divided into intervals of one frame
per second.  Roboflow was used to manually label 4,500 distinct frames for the following defect types:
●
Warping,
●
layer shifting,
●
under-extrusion, and
●
stringing
●
Under-extrusion
Bounding boxes and class labels were used to annotate each image.  Data augmentation included the following to
improve generalization:

Rotation: ±15°

Changes in brightness: ±20%

Horizontal flips
In the end, the dataset was increased to 5,000 photos, evenly distributed between normal examples and all defect
categories.
3.3.3 YOLOv8 Pipeline for Training and Inference
The following configuration was used to train a YOLOv8-small model on an NVIDIA RTX 3090 GPU for 100 epochs
using Ultralytics' PyTorch framework:
 ● Learning rate: 0.01 (cosine decay schedule) ● Batch size: 16
 ● Dataset split: 10% for testing, 10% for validation, and 80% for training
 On the validation set, the model's mAP@0.5:0.95 was 0.92.  On a system with 16 GB of RAM, real-time inference
ran at 18 frames per second.  To reduce false positives, a 5-frame sliding window logic was used. Robust anomaly
detection was ensured by limiting alerts to defects that recurred in three or more consecutive frames.
3.3.4 Time-Lapse Logger Based on the Edge
High-resolution stills were taken every 60 seconds using a Raspberry Pi 4B equipped with a secondary USB webcam
to supplement the real-time system.  To allow for sensor stabilization, a custom shell script using fswebcam skipped
the first 10 frames and recorded each frame after a 2-second lag.


---

## Page 13


For offline quality control, failure tracking, and dataset growth, every image was timestamped and saved.  Realtime, on-site data capture is made possible by the inexpensive, modular setup, which blends in perfectly with
contemporary edge computing paradigms and eliminates the need for expensive central infrastructure.
3.4 Analyzing Data and Making Comparisons
3.4.1 Assessment of Process Parameters
The following criteria were used to quantitatively analyze the post-processing of print quality:
 ● Dimensional accuracy (using 3D scanning and vernier calipers)
 ● Surface roughness (based on Ra values from profilometers)
 ● Mechanical performance (using standard ASTM D638 dogbone specimens to determine the Ultimate Tensile
Strength)
 The statistical significance of the main effects and interactions between the parameters was assessed using
Analysis of Variance (ANOVA).  Dominant influences on quality metrics were visualized with the aid of Pareto charts.
3.4.2 Geometric Sensitivity and Defect Density
The YOLOv8 system recorded the total number of defects in each print and grouped them according to type.  The
effect of geometry, specifically voids and overhangs in optimized parts, on defect frequency was evaluated through a
targeted analysis.  Light-weighted designs were found to exhibit a defect density that was 25–30% higher, particularly
at abrupt cross-sectional transitions.
3.4.3 Simulation of Closed-Loop Feedback
An algorithm for a hypothetical closed-loop feedback was modeled.  The nozzle temperature was raised by 5°C in the
middle of the print if more than five under-extrusion events per 1,000 layers were found.  This rule was applied
retroactively to assess possible decreases in the number of defects and material waste using historical defect
timestamps.
 The edge-device logger was also used to create a modular time-lapse capture tool.  This system does more than
just serve as a passive recorder; it lays the groundwork for the direct deployment of lightweight machine learning
models at the edge, providing early-stage image-based alerts prior to defects spreading into crucial geometries.
 These configurations make autonomous, intelligent quality control more practical for both regular FDM users and
research labs by offering a scalable and reasonably priced monitoring solution, particularly for extended-duration
prints or low-infrastructure settings.
The contrasting defect trends observed between standard and topology-optimized parts can be explained by their
underlying physics. Warping and stringing were reduced in optimized geometries because the lower thermal mass
allowed parts to cool and solidify faster, limiting the buildup of residual stresses and reducing filament bridging. On
the other hand, the thinner walls and narrow channels created by lightweighting increased the likelihood of underextrusion. These regions place greater demand on consiste filament flow, and even small disturbances in pressure or
cooling can cause incomplete deposition. This trade-off shows that while topology optimization can reduce thermal
defects, it also introduces geometry-sensitive challenges for extrusion reliability.


---

## Page 14


4. Results and Discussion of the Experiment
By analyzing both process-specific observations and data-driven insights gathered during the fabrication of aerospacegrade components using the Aion 500 printer, this section provides a thorough evaluation of the developed system.
Thermal stability, geometric effects on defect rates, parameter optimization, AI model performance, and the role of
auxiliary imaging systems are the main topics of the evaluation.  Key findings and their wider ramifications for the
additive manufacturing (AM) community are highlighted in the ensuing subsections.
4.1 Process Stability and Hardware Thermal Performance
For FDM printing to be successful, consistent heat conditions are essential, particularly when creating parts with fine
internal features and topology optimization.  Throughout a sequence of lengthy builds lasting more than six hours.
The Aion 500 kept the bed and nozzle temperatures within ±1 °C of the predetermined range.  High dimensional
stability and mechanical strength were achieved across prints thanks to the uniform melt flow and layer fusion made
possible by this narrow fluctuation band.
 On the other hand, attempts to print on the Creality series printer, which served as a baseline reference, showed
thermal variation of up to ±4 °C.  Increased instances of inter-layer delamination, irregular extrusion lines, and less
than ideal surface finish were all directly correlated with these discrepancies.  The comparison emphasizes how
important thermal stability is for maintaining repeatability and reducing variance in FDM output, especially for highperformance components with low tolerance to defect margins.
4.2 Optimizing Visual Monitoring and Camera Positioning
To maximize the real-time image acquisition system, three different camera mounting configurations were
experimentally tested: front-facing, side-mounted, and top-down.  The front-facing view continuously produced the
highest clarity in identifying edge-related anomalies and extrusion path disruptions, according to an analysis of more
than 1,500 images in various configurations. Defect types such as under-extrusion, stringing, and layer shift were
easier to see from this angle, particularly in the vicinity of the nozzle.  Consequently, the front-facing configuration
was used for all subsequent model training and real-time deployments, guaranteeing consistent data acquisition in line
with defect visibility.  For efficient visual inspection in additive workflows, this useful realization highlights the
necessity of camera placement strategies that are influenced by both hardware motion and optical geometry.

Fig 4.1: During a live printing operation, the AI system is seen in action in this picture, successfully detecting and flagging possible
problems on a component. Using the front-facing Raspberry Pi image logger, another included image shows an early-stage print of
an aerospace bracket on the Aion 500 that has been optimized for topology.  The nascent formation of support infill and the complex
contours of the optimized geometry are clearly visible in this visual record.

Another included image captures an early-stage print of a topology-optimized aerospace bracket on the Aion 500,
as documented via the front-facing Raspberry Pi image logger. This visual record distinctly shows the nascent
formation of support infill and the intricate contours of the optimized geometry beginning to take shape.


### Figures / Images on this page


![Page 14 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_14_image_01.png)


---

## Page 15


Fig 4.2: Real-time quality detection model is actively monitoring this 3D print for defects.
4.3 How Geometry Affects Print Quality and Types of Defects
The effect of geometry, specifically topology-optimized versus standard designs, on defect susceptibility was one of
the study's main findings.  Comparing the two design sets with the same set of parameters revealed the following:
 In topology-optimized sections, under-extrusion events were roughly 14% higher.  This is explained by the
structures' smaller mass and narrower internal channels, which make extrusion consistency difficult because of the
instability of filament flow and fast cooling.
 On the other hand, in optimized parts, warping and stringing defects dropped by 22% and 19%, respectively.
These enhancements most likely result from decreased mass and thermal inertia, which speed up solidification and
lessen the buildup of internal stress. The need for geometry-aware printing techniques is further supported by this dual
behavior. Process parameters that offset the increased vulnerability to flow inconsistencies must be used in conjunction
with designs that minimize weight and material consumption.  This draws attention to a larger trade-off: lightweighting
increases warp behavior and thermal stress profiles, but it also makes extrusion reliability and heat transfer dynamics
more sensitive, which is crucial for high-performance applications like aerospace.

Fig 4.3 : This system acts like a real-time copilot for the 3D printer, actively monitoring the live print for defects.
4.4 Statistical Analysis for Process Parameter Optimization
A thorough investigation of the ways in which three main print parameters—nozzle temperature, print speed, and
layer height—affect various quality metrics was made possible by the Box–Behnken experimental matrix.
Statistically significant trends were found using Analysis of Variance (ANOVA):


### Figures / Images on this page


![Page 15 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_15_image_01.png)


![Page 15 image 2](./AM_VM_SME_2619_Paper_17.04.2026_images/page_15_image_02.png)


---

## Page 16


 Nozzle temperature was the dominant factor impacting both surface finish and mechanical strength.  The ideal
melt viscosity was obtained at a mid-range temperature of 210°C, guaranteeing robust layer adhesion without
running the risk of nozzle blockage or overheating-induced stringing.
 Dimensional fidelity was significantly impacted by print speed.  Slower speeds introduced thermal gradients that
occasionally caused surface roughness, while speeds above 50 mm/s caused slight dimensional drift because of a
shorter filament settling time.
 Layer height mainly affected surface roughness and print resolution; 0.2 mm provided a fair compromise between
print time and resolution.
 Prints with the statistically ideal parameters of 210 °C, 50 mm/s, and 0.2 mm layer height were consistently
produced with:
 Average surface roughness (Ra): 4.2 μm
 The ultimate tensile strength is 35 MPa, and the dimension accuracy is ±0.15 mm.
 For aerospace applications where mechanical robustness and surface finish must coexist, these values represent a
good compromise.  The advantage of structured experimental planning over heuristic tuning for obtaining highreliability prints is further supported by the statistical insight.
4.5 YOLOv8-Based Real-Time Monitoring Performance
On non-GPU hardware, the trained YOLOv8-small model showed good real-time performance, inferring at 20 frames
per second on an Intel i7 workstation.  With the following per-defect category precision, the model, which was trained
on a varied dataset of 22,500 annotated images, achieved an impressive mAP@0.5:0.95 of 91.3%:

89% strung

92% under-extrusion

94% of layer shifting

Warping: 90%
 The model's high recall during real-world deployments (93%) and low false positive rate (<4%) further confirmed
its dependability.  The system identified a persistent under-extrusion anomaly during layer 152 in one crucial usecase.  The operator was able to stop the process and carry out maintenance because of the timely alert. Consequently,
a six-hour print failure is avoided.  The efficiency of lightweight, real-time AI models in lowering material waste,
operational downtime, and manual oversight burdens is demonstrated by this practical intervention.  The findings also
support YOLOv8-small's feasibility for use on edge devices with moderate performance, providing a promising
avenue for integrated defect detection tools in upcoming printer firmware or inexpensive monitoring kits.


---

## Page 17


Fig 4.5: This AI system is capable of actively monitoring the 3D printer

Fig 4.5.2: The early stages of making a topology-optimized aerospace bracket on the Aion 500 FDM printer, captured by a
Raspberry Pi-based time-lapse camera. This image shows the steady flow of material and the beginning of a complex shape.
4.6 Role and Contribution of Time-Lapse Image Logging
The Raspberry Pi-based time-lapse logger made a substantial contribution to offline diagnostics and dataset expansion,
while the YOLOv8 system handled real-time monitoring.  It consistently took more than 3,500 high-resolution still
photos at one-minute intervals during 60 hours of printing.
 In a number of instances, this system made it possible to detect subtle abnormalities that were not visible in the
real-time feed, like progressive nozzle-height deviations and thermally-induced deformations.  These visual cues
helped guide later research into nozzle wear and mechanical alignment problems.
  Without the need for specialized image acquisition runs, time-lapse photos were repurposed to supplement the
training dataset and aid in ongoing model improvement.  Since edge-based AI analysis is still in its infancy, the
Raspberry Pi system's resilience, affordability, and ease of integration show that adding passive monitoring modules
to industrial 3D printing settings is feasible.


### Figures / Images on this page


![Page 17 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_17_image_01.png)


![Page 17 image 2](./AM_VM_SME_2619_Paper_17.04.2026_images/page_17_image_02.png)


---

## Page 18


Fig 4.6 : This image shows the system's smart abilities, like identifying a specific print problem and suggesting a fix.

Fig 4.7 : This image is similar to the previous one, showing how the system can detect another type of print issue and offer a
solution.
4.7 Implications and Generalization
A very robust framework for defect minimization and quality assurance in FDM was produced by the comprehensive
strategy described in this study, which combined geometry-aware design, parameter optimization, AI-based
monitoring, and edge-device-assisted logging.  Such a system's robustness and adaptability are confirmed by the fact
that it operated consistently across extended builds, different geometries, and a variety of parameter sets.
 Less print failures, better material utilization, and increased reproducibility were the outcomes of the demonstrated
synergy between optimized design, adjusted parameters, and AI intervention. These outcomes are essential for moving
additive manufacturing from prototyping to production-grade reliability. A replicable standard for intelligent AM
process control is also established by the monitoring pipeline's modular architecture, which guarantees that it can be
modified to fit different printer models, materials, and manufacturing domains. Although the defect detection model
was primarily trained and tested on the Aion 500 printer using PLA, the design of the dataset and training process was
aimed at making it broadly applicable. To avoid overfitting, we introduced variations in lighting, orientation, scaling,


### Figures / Images on this page


![Page 18 image 1](./AM_VM_SME_2619_Paper_17.04.2026_images/page_18_image_01.png)


![Page 18 image 2](./AM_VM_SME_2619_Paper_17.04.2026_images/page_18_image_02.png)


---

## Page 19


and defect severity during annotation. The four defects addressed—stringing, under-extrusion, warping, and layer
shifting—are not unique to the Aion 500 but are commonly observed in FDM processes, regardless of printer type or
filament. This gives confidence that the trained model can adapt to other setups with minimal fine-tuning. As part of
future work, we intend to validate the system on different machines such as Prusa and Creality models, and with
materials like ABS, PETG, and carbon-reinforced composites, to confirm its robustness in more diverse manufacturing
conditions.
5. Conclusion and Upcoming Projects
With an emphasis on lightweight part fabrication for aerospace and automotive applications, this study offers a
thorough and modular framework for improving the quality, effectiveness, and dependability of fused deposition
modeling (FDM).  The suggested method shows quantifiable gains in a number of print quality and process robustness
dimensions by methodically combining design optimization, controlled experimentation, real-time defect detection,
and edge-based monitoring.
5.1 Synopsis of Contributions: Optimizing Process Parameters to Improve
Finding the ideal process parameters was made possible by a systematic experimental strategy based on the Box–
Behnken design.  The optimal setup, which included a nozzle temperature of 210°C, a print speed of 50 mm/s, and a
layer height of 0.20 mm, produced a:
 Volumetric error is reduced by 34%, surface roughness is improved by 27%, dimensional consistency is increased
by 40%, and ultimate tensile strength is increased by 15%.
 For high-performance parts that must meet strict tolerances, these metrics highlight how crucial precisely
controlled thermal and material flow conditions are to achieving mechanical integrity and geometric accuracy.
Defect Variation Driven by Geometry in Topology-Optimized Components : By contrasting standard and
topology-optimized aerospace brackets, the influence of part geometry was carefully assessed.  The latter
demonstrated notable defect suppression, including:
● 22% reduction in warping
● 19% reduction in stringing, despite a 14% increase in under-extrusion due to narrow walls and shortened
extrusion paths.
Given that geometry-induced thermal dynamics can both decrease and increase the risk of certain defects, this
duality emphasizes the need to combine lightweight design with adaptive printing techniques.  To prevent adding
instability to the print, process parameters and slicing profiles must be sensitive to the underlying part geometry.
 AI-Assisted Real-Time YOLOv8 Defect Detection : A mean Average Precision (mAP@0.5:0.95) of 91.3% was
attained by the deployment of the YOLOv8-small model, which was trained on a varied dataset of 22,500 labeled
images. With a real-time inference rate of 20 FPS on a typical i7 workstation, the accuracy of individual defect
classification ranged from 89% to 94%, enabling prompt feedback and operator intervention.  With false alarm rates
under 4%, the model continuously showed a 93% detection accuracy.  Crucially, by combining alert-driven G-code
pauses with user-guided maintenance actions, this system not only detected flaws but also made semi-autonomous
process correction easier.
Visual Logging and Data Archiving on the EdgeMore than 3,600 high-resolution still images were taken during
60 print hours using a Raspberry Pi-based logger, which offered crucial archival and diagnostic assistance.  In one
case, time-lapse images revealed a subtle change in nozzle height that was not visible in real-time video, providing a
deeper
understanding
of
the
underlying
cause.
This inexpensive module's consistent, crash-free operation confirms its dependability for training data generation and
passive monitoring.  This demonstrates that decentralized, edge-driven monitoring systems are useful instruments for
expanding AM processes.
5.2 Context-Aware Diagnostic Feedback: Going Beyond Detection
The monitoring framework’s shift from simple detection to guided diagnostic feedback is an important step forward.
While the system does not yet alter machine parameters during printing, it provides targeted recommendations to the
operator, simulating the benefits of closed-loop quality control.  The system was improved in the most recent testing
to provide context-specific remedial recommendations in addition to classifying defects found.  For instance, the


---

## Page 20


system indicated "Incorrect Geometry" when it detected geometric anomalies and suggested "Check the STL file for
mesh-errors or revise slicer configurations."
When the alert detected initial-layer separation, it labeled the flaw as "Warping" and suggested "Enable heated bed
and improve first-layer adhesion using glue or tape."
This development represents a paradigm change from static alerting to interactive quality control, which provides
prompt, useful guidance based on the type of defect.  Such diagnostic assistance is especially helpful for inexperienced
users and simplifies decision-making for more experienced users who want a quicker fix.
 Although the system architecture lays the groundwork for autonomous corrective actions in subsequent iterations,
the current feedback is mainly text-based. This could enable real-time adjustment of parameters like bed temperature,
print speed, or fan control based on implied root causes.  This sets up the system as a precursor to fully closed-loop
additive manufacturing, in which intelligent agents autonomously intervene to preserve quality and prevent failure in
addition to observing.
5.3 Future Work and Opportunities
The findings of this study provide a strong basis for the development of autonomous additive manufacturing systems.
Several important paths are anticipated going forward:
 ● Multi-Modal Sensor Integration: To increase the sensory footprint and enhance the precision of defect detection,
future research can include thermal, acoustic, or vibration data.
 ● Implementation of Closed-Loop Control: Building on the feedback algorithm's success, future iterations will
test real-time G-code modulation to automatically fix new flaws.
 Generalization Across Materials and Printers: The framework's robustness and transferability will be evaluated
through validation across various materials (such as carbon-reinforced PLA, PETG, or composites) and printer
models.
 Federated Learning Models: Without centralized data sharing, models can be updated across dispersed printers
with the right privacy protections, allowing for community-driven improvement in defect classification.
5.4 Closing Remarks
This study offers a comprehensive and verified framework for enhancing the scalability, quality, and dependability of
fused deposition modeling (FDM) in the manufacturing of lightweight structural elements.  Combining real-time AIdriven defect detection, intelligent process tuning, and geometric optimization
6. Implications of the Research
In addition to advancing scholarly knowledge, the study offers practical and understandable insights for system
designers and industrial practitioners.  This work has implications for the fields of computer vision, engineering,
manufacturing, and intelligent systems.
6.1 Useful Consequences for the Additive Manufacturing Sector
The suggested framework acts as a useful guide for improving industrial FDM workflows' throughput and reliability.
The determination of the ideal process parameters, namely a nozzle temperature of 210°C, a print speed of 50 mm/s,
and a layer height of 0.20 mm, showed measurable advantages, such as:
● A 15% increase in tensile strength
● A notable decrease in volumetric error and dimensional deviations
● Better surface finish consistency between batches
These enhancements confirm how crucial precise extrusion calibration and strict heat control are to the production
of functional-grade parts.  The study emphasizes that in order to fully realize the potential of optimized settings,
industrial-grade systems with mechanical stability and high-fidelity temperature regulation, such as the Aion 500, are
essential.  This shift makes FDM a competitive option for end-use parts that require repeatability, structural integrity,
and geometric accuracy in addition to being a prototyping tool for aerospace and automotive applications.


---

## Page 21


6.2 AI Developments for Manufacturing Quality Assurance
The effective implementation of a real-time AI-based defect detection system using YOLOv8-small is a key
contribution of this work.  At a rate of 20 frames per second, a mean Average Precision (mAP@0.5:0.95) of
91.3% was attained.
The model substitutes an effective and automated method for manual inspection.  The advantages include:
● High-precision alerts with classification accuracies ranging from 89% to 94% across multiple defect types
● Early intervention in defect propagation, such as stopping a six-hour print mid-process to prevent material waste
 Trust in automated decision-making is made possible by low false positive rates.
 Importantly, by providing context-aware feedback and making remedial recommendations in natural language,
the system goes beyond standard visual inspection.  To reduce first-layer warping, for example: "Check the STL file
for non-manifold geometry" for deformed sections; and "Increase bed temperature and use adhesion promoters."
 By lowering dependency on domain expertise and enhancing operational resilience, this capability represents a
significant step forward toward intelligent, user-assistive manufacturing.  Additionally, it facilitates proactive, userfriendly quality control workflows that are appropriate for both industrial operators and inexperienced users.
6.3 Bridging the Design-Manufacturing Divide
The study confirms that part geometry and defect susceptibility are interdependent, particularly when using
sophisticated topology optimization techniques.  The lightweight bracket designs showed a 14% increase in underextrusion, especially in areas with thin, unsupported walls, despite being advantageous in reducing material use and
thermal stress-induced defects (e.g., 22% less warping, 19% less stringing).
 The Design for Additive Manufacturing (DfAM) philosophy is supported by these results, which highlight the
necessity of co-optimizing process parameters and design geometry for high-performance prints.  For design
engineers, the ability of AI systems to examine process anomalies in real time provides a vital feedback loop.
Intelligent design adaptation, where process-aware models inform geometry decisions upstream, could be made
possible by integrating such data-driven insights into CAD and slicing environments. This would help close the longstanding gap between digital design and physical realization.
6.4 Effects on Economic and Operational Efficiency
Operationally speaking, the integrated approach results in noticeable improvements in resource optimization and cost
effectiveness:
Defect prevention reduced material waste, automated monitoring reduced manual inspection time, and early
anomaly detection reduced reprints.
Over the course of 60 hours of printing, this system managed to capture over 3,600 high-resolution images,
allowing for thorough root-cause analysis and model retraining without interfering with the process.  It is appropriate
for integration in a variety of settings, including industrial production floors and research labs, due to its low cost,
high reliability, and platform independence.
 Furthermore, the system's worth in long-term process optimization is highlighted by its capacity to detect minute
irregularities like layer misalignments or slow nozzle drift.  By decreasing downtime caused by defects, improving
overall manufacturing sustainability, and raising yield in additive manufacturing operations, these insights support
continuous improvement practices.
References
1. L. Xu, X. Zhang, F. Ma, G. Chang, C. Zhang, J. Li, S. Wang, Y. Huang, Detecting defects in fused deposition
modelling based on improved YOLO v4. Mater. Res. Express 10, 10.1088/2053-1591/acf6f9 (2023).
2. J. Zhou, H. Li, L. Lu, Y. Cheng, Machine Vision-Based Surface Defect Detection Study for Ceramic 3D
Printing. Machines 12, 166 (2024).
3. J. Ye, A Machine Learning Algorithm to Aid the Development of Repair Materials for Ancient Ceramics via
Additive Manufacturing. Processes 13, 145 (2025).
4. J. Zhang, J. Xu, L. Zhu et al., An improved MobileNet-SSD algorithm for automatic defect detection on
vehicle body paint. Multimed. Tools Appl. 79, 23367-23385 (2020).


---

## Page 22


5. X. Wang, L. Huang, Y. Li, Y. Wang, X. Lu, Z. Wei, Q. Mo, S. Zhang, Y. Sheng, C. Huang, H. Zhao, Y. Liu,
Research progress in polylactic acid processing for 3D printing. J. Manuf. Process. 112, 161-178 (2024).
6. N. Ramos, C. Mittermeier, J. Kiendl, Experimental and numerical investigations on heat transfer in fused
filament fabrication 3D-printed specimens. Int. J. Adv. Manuf. Technol. 118, 1367-1381 (2022).
7. A. Paul, M. Mozaffar, Z. Yang, W. Liao, A. Choudhary, J. Cao, A. Agrawal, A real-time iterative machine
learning approach for temperature profile prediction in additive manufacturing processes. (2019).
8. A. Boschetto, L. Bottini, L. Macera, S. Vatanparast, Additive Manufacturing for Lightweighting Satellite
Platform. Appl. Sci. 13, 2809 (2023).
9. R. Zhang, Y. Li, Z. Guan, Research on injection moulded parts defect detection algorithm based on
multiplicative feature fusion and improved attention mechanism. Sci. Rep. 14, 30864 (2024).
10. J. Zhu, W. Zhang, L. Xia, Topology Optimization in Aircraft and Aerospace Structures Design. Arch.
Comput. Methods Eng. 22, 509-521 (2015).
11. M. Zhu, B. Chen, D. Kalenichenko, W. Wang, T. Weyand, M. Andreetto, H. Adam, MobileNets: Efficient
Convolutional Neural Networks for Mobile Vision Applications. (2017).
12. Z. Liu, G. Xiao, H. Liu, H. Wei, Multi-Sensor Measurement and Data Fusion. IEEE Instrum. Meas. Mag.
(2022).
13. K. Chen, P. Zhang, H. Yan, G. Chen, T. Sun, Q. Lu, Y. Chen, H. Shi, A review of machine learning in
additive manufacturing: design and process. Int. J. Adv. Manuf. Technol. 135, 1051-1087 (2024).
14. H. Y. Chia, J. Wu, X. Wang, W. Yan, Process parameter optimization of metal additive manufacturing: a
review and outlook. J. Mater. Informatics 2, 16 (2022).
15. Z. Jiang, L. Zhao, S. Li, Y. Jia, Real-time object detection method based on improved YOLOv4-tiny. (2020).
