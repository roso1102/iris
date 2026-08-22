# Golden-set label audit — human adjudication sheet

For each flagged query decide: label wrong (fix the JSON) or retrieval wrong (leave label; it's a real failure).

**25 of 50 queries flagged** ({'OFF_BY_ONE': 13, 'PAGE_MISS': 7, 'OK': 25, 'DOC_MISS': 5}).

---

## q_001 [OFF_BY_ONE] (direct_factual)

- **Query:** What term is used by Knudsen (2020) to describe the conversion of data from analogue to digital format?
- **Label:** docs `doc_006`, pages `1`
- **Expected answer:** Digitisation.
- **Evidence:** labeled page [1], retrieval hits [2] (adjacent)
- **Top-5 retrieved:** doc_006@p2 | doc_006@p5 | doc_006@p13 | doc_006@p8 | doc_006@p31
- **Top snippet:** 1 Knudsen (2020) distinguishes between digitisation and digitalisation, where digitisation is depicted as the process of converting data from a traditional, analogue format to a digital format whilst ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_002 [OFF_BY_ONE] (direct_factual)

- **Query:** In what year did the US SEC establish the XBRL Voluntary Filing Program (VFP)?
- **Label:** docs `doc_006`, pages `13`
- **Expected answer:** 2005.
- **Evidence:** labeled page [13], retrieval hits [14] (adjacent)
- **Top-5 retrieved:** doc_006@p14 | doc_006@p29 | doc_006@p34 | doc_006@p28 | doc_006@p30
- **Top snippet:** 5 The US SEC established the VFP to serve as a test of XBRL's capacity for filing corporate financial information, and  to  help  regulators  understand  the  associated  costs  to  filers  and  the  ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_003 [PAGE_MISS] (direct_factual)

- **Query:** What markup language was announced by JP Morgan and PricewaterhouseCoopers to exchange information on financial derivatives?
- **Label:** docs `doc_007`, pages `41`
- **Expected answer:** FpML (Financial Products Markup Language).
- **Evidence:** labeled pages [41], retrieval pages of labeled docs: [22, 24, 32, 33, 61, 66, 67, 68]
- **Top-5 retrieved:** doc_007@p32 | doc_007@p33 | doc_007@p66 | doc_007@p61 | doc_007@p24
- **Top snippet:** Use  in  Business  Reporting: XML  is  a  relatively  new  development,  but  one  in  which interest  is  growing  rapidly  in  a  variety  of  areas  where  information  must  be  exchanged between ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_005 [OFF_BY_ONE] (direct_factual)

- **Query:** According to the 15th Finance Commission guidelines, what percentage of the NDRMF is kept for Preparedness and Capacity-building activities?
- **Label:** docs `doc_003`, pages `9`
- **Expected answer:** 10 per cent of the annual allocation of SDRMF.
- **Evidence:** labeled page [9], retrieval hits [10] (adjacent)
- **Top-5 retrieved:** doc_003@p20 | doc_003@p10 | doc_003@p19 | doc_003@p19 | doc_003@p19
- **Top snippet:** 2.4 These guidelines are for the operation and administration of the NDRF for disasters as notified by the Central Government for SDRF and NDRF. However, guidelines in respect of SDMF & NDMF; and for ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_006 [PAGE_MISS] (direct_factual)

- **Query:** What is the name of the hypothetical example from the Jenkins report that the FASB transformed into an online report?
- **Label:** docs `doc_007`, pages `9`
- **Expected answer:** Faux.Com.
- **Evidence:** labeled pages [9], retrieval pages of labeled docs: [1, 2, 12, 19, 49, 66, 79]
- **Top-5 retrieved:** doc_007@p19 | doc_007@p12 | doc_007@p49 | doc_007@p1 | doc_007@p66
- **Top snippet:** The Financial Accounting Standards Board (FASB) in the USA and the Canadian Institute of Chartered Accountants (CICA) are both researching Web-based business reporting. The FASB is undertaking this as...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_009 [DOC_MISS] (direct_factual)

- **Query:** What is the maximum term of imprisonment under Section 9 of the Public Records Act, 1993 for contraventions?
- **Label:** docs `doc_001`, pages `5`
- **Expected answer:** Imprisonment for a term which may extend to five years.
- **Evidence:** labeled docs ['doc_001'], top-10 docs ['doc_002', 'doc_003', 'doc_007']
- **Top-5 retrieved:** doc_002@p3 | doc_007@p15 | doc_003@p14 | doc_002@p4 | doc_007@p44
- **Top snippet:** ```markdown Form-1 [See sub-rule (2) of rule 5] Particulars of records of permanent nature due for appraisal during the year.....  | Total number of files of 'A' & 'B' categories lying in the records ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_010 [PAGE_MISS] (direct_factual)

- **Query:** Under the revised NDRF norms of July 2023, what is the Ex-Gratia payment for grievous injury requiring hospitalization for more than a week?
- **Label:** docs `doc_008`, pages `1`
- **Expected answer:** Rs. 16,000/- per person.
- **Evidence:** labeled pages [1], retrieval pages of labeled docs: [3, 11]
- **Top-5 retrieved:** doc_008@p3 | doc_003@p9 | doc_003@p24 | doc_003@p23 | doc_003@p22
- **Top snippet:** | S.No. | Items | Norms of Assistance | | :---- | :---- | :-------------------- | | A     | Response & Relief [40% of State Disaster Risk Management Fund (SDRMF) i.e. equal to 50% of SDRF allocation f...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_011 [OFF_BY_ONE] (multi_hop)

- **Query:** Does the definition of 'records officer' in the Public Records Act 1993 align with the rank required in the 1997 Rules?
- **Label:** docs `doc_001;doc_002`, pages `1;2`
- **Expected answer:** The 1993 Act defines a records officer generally under Section 2(g), while Rule 3 of the 1997 Rules specifically mandate
- **Evidence:** labeled page [1, 2], retrieval hits [3] (adjacent)
- **Top-5 retrieved:** doc_002@p3 | doc_007@p65 | doc_007@p55 | doc_003@p5 | doc_002@p4
- **Top snippet:** ```markdown Form-1 [See sub-rule (2) of rule 5] Particulars of records of permanent nature due for appraisal during the year.....  | Total number of files of 'A' & 'B' categories lying in the records ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_013 [PAGE_MISS] (multi_hop)

- **Query:** Which standard-setting bodies were actively researching Web-based business reporting, and what XML initiative was announced by the AICPA?
- **Label:** docs `doc_007`, pages `9;42`
- **Expected answer:** FASB and CICA were researching Web-based business reporting. The AICPA announced the eXtensible Financial Reporting Mark
- **Evidence:** labeled pages [9, 42], retrieval pages of labeled docs: [3, 6, 13, 19, 32, 33, 46, 72]
- **Top-5 retrieved:** doc_007@p33 | doc_007@p72 | doc_007@p32 | doc_006@p28 | doc_007@p46
- **Top snippet:** Issues: Successful  migration  of  accounting  information  beyond  the  bounds  of  individual corporate  Web  sites  will  require attribute  recognition -  the  ability  of  both  humans  and softw...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_017 [OFF_BY_ONE] (multi_hop)

- **Query:** If the SEC extends Gratuitous Relief for an earthquake beyond 60 days, does this violate the July 2023 NDRF norms?
- **Label:** docs `doc_008`, pages `2`
- **Expected answer:** No. Depending on the ground situation, the SEC can extend the time period beyond the prescribed limits as long as the ex
- **Evidence:** labeled page [2], retrieval hits [3] (adjacent)
- **Top-5 retrieved:** doc_003@p8 | doc_008@p5 | doc_008@p3 | doc_003@p10 | doc_003@p3
- **Top snippet:** (vii) The release of installments shall be made by Department of Expenditure, Ministry of Finance, after receiving due recommendations from the Ministry of Home Affairs (DM Division).  State Executive...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_018 [OFF_BY_ONE] (multi_hop)

- **Query:** How does the Public Records Act define 'public records', and who is permitted to downgrade their classification?
- **Label:** docs `doc_001;doc_002`, pages `2`
- **Expected answer:** The Act defines public records to include documents, manuscripts, files, microfilms, and computer records. The Rules spe
- **Evidence:** labeled page [2], retrieval hits [3] (adjacent)
- **Top-5 retrieved:** doc_002@p3 | doc_002@p4 | doc_003@p14 | doc_007@p39 | doc_007@p15
- **Top snippet:** ```markdown Form-1 [See sub-rule (2) of rule 5] Particulars of records of permanent nature due for appraisal during the year.....  | Total number of files of 'A' & 'B' categories lying in the records ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_020 [PAGE_MISS] (multi_hop)

- **Query:** Is XBRL based on a W3C standard? If so, what is it?
- **Label:** docs `doc_007`, pages `41`
- **Expected answer:** Yes, XBRL is an application of XML (eXtensible Markup Language), which is a standard defined by the W3 Consortium.
- **Evidence:** labeled pages [41], retrieval pages of labeled docs: [32, 61, 66]
- **Top-5 retrieved:** doc_006@p6 | doc_006@p7 | doc_006@p23 | doc_006@p28 | doc_007@p32
- **Top snippet:** A corporate report is converted into a digital corporate report when it is structured with XBRL tags that convey the contextual meaning of reported information. The contextual tags are listed, classif...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_021 [OFF_BY_ONE] (table_interpretation)

- **Query:** Based on the State-wise allocation of SDRF table, what is the Central Share allocated to Bihar for the 2024-25 period?
- **Label:** docs `doc_003`, pages `14`
- **Expected answer:** 1,311.20 crore.
- **Evidence:** labeled page [14], retrieval hits [15] (adjacent)
- **Top-5 retrieved:** doc_003@p15 | doc_003@p18 | doc_003@p6 | doc_003@p20 | doc_003@p20
- **Top snippet:** Here's the accurately extracted text from the image, preserving its layout structure:  Annexure-l  State-wise allocation of State Disaster Response Fund (SDRF) for the Award period 2021-26  (Rs. in cr...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_028 [PAGE_MISS] (table_interpretation)

- **Query:** In the Financial Information Disclosed table by Hussey et al. (1998), how many UK FTSE 100 companies published Detailed Accounts in March 1998?
- **Label:** docs `doc_007`, pages `47`
- **Expected answer:** 54 companies (85.7%).
- **Evidence:** labeled pages [47], retrieval pages of labeled docs: [15, 19, 35, 36, 37, 38, 74, 75]
- **Top-5 retrieved:** doc_007@p36 | doc_007@p35 | doc_007@p37 | doc_007@p38 | doc_007@p15
- **Top snippet:** Table 2: Financial Information Disclosed - UK FTSE 100 Companies....

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_029 [OFF_BY_ONE] (table_interpretation)

- **Query:** What is the Central Share for Maharashtra in the 2021-22 SDRF allocation?
- **Label:** docs `doc_003`, pages `14`
- **Expected answer:** 1,456.00 crore.
- **Evidence:** labeled page [14], retrieval hits [15] (adjacent)
- **Top-5 retrieved:** doc_003@p15 | doc_003@p6 | doc_003@p20 | doc_003@p2 | doc_003@p2
- **Top snippet:** Here's the accurately extracted text from the image, preserving its layout structure:  Annexure-l  State-wise allocation of State Disaster Response Fund (SDRF) for the Award period 2021-26  (Rs. in cr...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_030 [OFF_BY_ONE] (table_interpretation)

- **Query:** What was the total State Share allocation for Goa across the 2021-26 period?
- **Label:** docs `doc_003`, pages `14`
- **Expected answer:** 16.00 crore.
- **Evidence:** labeled page [14], retrieval hits [15] (adjacent)
- **Top-5 retrieved:** doc_003@p15 | doc_003@p15 | doc_003@p15 | doc_003@p20 | doc_003@p18
- **Top snippet:** Here's the accurately extracted text from the image, preserving its layout structure:  Annexure-l  State-wise allocation of State Disaster Response Fund (SDRF) for the Award period 2021-26  (Rs. in cr...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_033 [OFF_BY_ONE] (scanned_lookup)

- **Query:** According to the revised SDRF norms, what is the maximum assistance for the loss of a camel, horse, or bullock acting as a draught animal?
- **Label:** docs `doc_008`, pages `5`
- **Expected answer:** Rs. 32,000/- per animal.
- **Evidence:** labeled page [5], retrieval hits [6] (adjacent)
- **Top-5 retrieved:** doc_008@p7 | doc_008@p3 | doc_003@p23 | doc_008@p9 | doc_008@p6
- **Top snippet:** ```markdown | | | | |---|---|---| | | b) Perennial crops/Agro forestry (Plantation in own farmland) | Rs. 22,500/- ha. for all types of perennial crops/ Agro forestry (Plantation in own farmland), sub...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_034 [DOC_MISS] (scanned_lookup)

- **Query:** What is the specific penalty or action for unauthorized removal of public records by a records officer under the 1993 Act?
- **Label:** docs `doc_001`, pages `4;5`
- **Expected answer:** Under Section 7, the records officer must take appropriate action for recovery/restoration and submit a report without d
- **Evidence:** labeled docs ['doc_001'], top-10 docs ['doc_002', 'doc_003', 'doc_007', 'doc_008']
- **Top-5 retrieved:** doc_002@p3 | doc_003@p1 | doc_007@p2 | doc_007@p44 | doc_003@p5
- **Top snippet:** ```markdown Form-1 [See sub-rule (2) of rule 5] Particulars of records of permanent nature due for appraisal during the year.....  | Total number of files of 'A' & 'B' categories lying in the records ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_035 [PAGE_MISS] (scanned_lookup)

- **Query:** Form-8 in the Public Records Rules 1997 is used for what purpose?
- **Label:** docs `doc_002`, pages `7`
- **Expected answer:** It is the Application form for permission to consult records by a research scholar.
- **Evidence:** labeled pages [7], retrieval pages of labeled docs: [3, 4]
- **Top-5 retrieved:** doc_002@p3 | doc_007@p44 | doc_007@p15 | doc_003@p1 | doc_007@p72
- **Top snippet:** ```markdown Form-1 [See sub-rule (2) of rule 5] Particulars of records of permanent nature due for appraisal during the year.....  | Total number of files of 'A' & 'B' categories lying in the records ...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_038 [DOC_MISS] (scanned_lookup)

- **Query:** Who serves as the ex-officio Chairman of the Archival Advisory Board?
- **Label:** docs `doc_001`, pages `5`
- **Expected answer:** The Secretary to the Government of India in the Ministry of Central Government dealing with culture.
- **Evidence:** labeled docs ['doc_001'], top-10 docs ['doc_003', 'doc_006', 'doc_007']
- **Top-5 retrieved:** doc_007@p6 | doc_007@p1 | doc_006@p31 | doc_007@p77 | doc_003@p8
- **Top snippet:** We looked outside our organisation for assistance. IASC has been most fortunate to benefit from the collaboration of four talented researchers. Andrew Lymer, Roger Debreceny, Glen Gray, and Asheq Rahm...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_041 [DOC_MISS] (short_ambiguous)

- **Query:** What about clause 5?
- **Label:** docs `doc_001`, pages `3`
- **Expected answer:** Section 5 of the Public Records Act 1993 requires every records creating agency to nominate an officer as a records offi
- **Evidence:** labeled docs ['doc_001'], top-10 docs ['doc_003', 'doc_004', 'doc_007']
- **Top-5 retrieved:** doc_007@p61 | doc_004@p1 | doc_007@p15 | doc_007@p60 | doc_007@p64
- **Top snippet:** 5.6  FORM OF A WEB BUSINESS REPORTING STANDARD...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_042 [OFF_BY_ONE] (short_ambiguous)

- **Query:** Summarize the risks of plug-ins.
- **Label:** docs `doc_007`, pages `31`
- **Expected answer:** Plug-ins pose a computer security risk. If a file contains a virus or Trojan horse, the plug-in executing automatically 
- **Evidence:** labeled page [31], retrieval hits [30] (adjacent)
- **Top-5 retrieved:** doc_007@p27 | doc_007@p26 | doc_007@p30 | doc_007@p3 | doc_007@p27
- **Top snippet:** Plug-ins are also a computer security risk. With plug-ins, when users click on links to files that  requires  plug-ins,  the  plug-ins  will  automatically  launch. If  the  file  has  a  virus  or Tr...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_045 [OFF_BY_ONE] (short_ambiguous)

- **Query:** How much for a dead cow?
- **Label:** docs `doc_008`, pages `5`
- **Expected answer:** Rs. 37,500/- per animal for a milch cow, yak, camel, or buffalo under the SDRF/NDRF animal husbandry assistance norms.
- **Evidence:** labeled page [5], retrieval hits [6] (adjacent)
- **Top-5 retrieved:** doc_008@p7 | doc_008@p6 | doc_007@p43 | doc_007@p32 | doc_007@p60
- **Top snippet:** ```markdown | | | | |---|---|---| | | b) Perennial crops/Agro forestry (Plantation in own farmland) | Rs. 22,500/- ha. for all types of perennial crops/ Agro forestry (Plantation in own farmland), sub...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_048 [DOC_MISS] (short_ambiguous)

- **Query:** When does the act come into force?
- **Label:** docs `doc_001`, pages `1`
- **Expected answer:** The Public Records Act 1993 comes into force on such date as the Central Government may appoint by notification in the O
- **Evidence:** labeled docs ['doc_001'], top-10 docs ['doc_003', 'doc_004', 'doc_005', 'doc_006', 'doc_007']
- **Top-5 retrieved:** doc_003@p4 | doc_003@p19 | doc_003@p1 | doc_004@p1 | doc_005@p8
- **Top snippet:** notifications establishing SDRF as per section 48(1) (a) of the DM Act, 2005 is in force. A copy of the same may be provided to the MHA....

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

## q_049 [OFF_BY_ONE] (short_ambiguous)

- **Query:** Any help for weavers?
- **Label:** docs `doc_008`, pages `8`
- **Expected answer:** Yes, assistance to artisans for handicrafts/handloom includes Rs. 5,000 per artisan for the replacement of damaged funct
- **Evidence:** labeled page [8], retrieval hits [7] (adjacent)
- **Top-5 retrieved:** doc_007@p28 | doc_007@p12 | doc_007@p59 | doc_007@p7 | doc_008@p10
- **Top snippet:** 66 See purl.org/dc/...

- [ ] label wrong -> fix goldendataset.json
- [ ] label right -> genuine retrieval failure

