export const LAB_CATEGORIES = [
  'Electrocardiogram (ECG)',
  'Treadmill Test (TMT)',
  'Ultrasound Scan',
  '2D Echocardiogram (2D Echo)',
  'Mammography',
  'Dual-Energy X-ray Absorptiometry (DEXA) Scan',
  'X-Ray Imaging',
  'Pure Tone Audiometry',
  'Ophthalmology Examination',
  'Pap Smear Test',
  'Urine Examination (Input Condition: Bladder needs to be full)',
  'Stool Examination',
  'Blood Test (Includes all Pathology, Biochemistry, Hematology, Immunology, and Genetics)',
] as const;

export type DefinedLabCategory = (typeof LAB_CATEGORIES)[number];
