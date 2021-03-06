from FWCore.ParameterSet.VarParsing import VarParsing

options =VarParsing('analysis')
options.register('config', default = '', mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.string, info = 'Single-switch config. Values: 03Feb2017, 23Sep2016, Spring16, Summer16')
options.register('globaltag', default = '', mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.string, info = 'Global tag')
options.register('connect', default = '', mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.string, info = 'Globaltag connect')
options.register('lumilist', default = '', mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.string, info = 'Good lumi list JSON')
options.register('isData', default = False, mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.bool, info = 'True if running on Data, False if running on MC')
options.register('useTrigger', default = True, mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.bool, info = 'Fill trigger information')
options.register('printLevel', default = 0, mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.int, info = 'Debug level of the ntuplizer')
options.register('skipEvents', default = 0, mult = VarParsing.multiplicity.singleton, mytype = VarParsing.varType.int, info = 'Skip first events')
options._tags.pop('numEvent%d')
options._tagOrder.remove('numEvent%d')

options.parseArguments()

jetMETReco = True
muEGFixed = False
egmSmearingType = 'Moriond2017_JEC'
if options.config == '03Feb2017':
    jetMETReco = False
    muEGFixed = True
    options.isData = True
    options.globaltag = '80X_dataRun2_2016SeptRepro_v7'
elif options.config == '23Sep2016':
    options.isData = True
    options.globaltag = '80X_dataRun2_2016SeptRepro_v7'
elif options.config == 'Spring16':
    options.isData = False
    options.globaltag = '80X_mcRun2_asymptotic_2016_v3'
elif options.config == 'Summer16':
    options.isData = False
    options.globaltag = '80X_mcRun2_asymptotic_2016_TrancheIV_v8'
elif options.config:
    raise RuntimeError('Unknown config ' + options.config)

if options.config == '03Feb2017' or options.config == '23Sep2016':
    import os

    jsonDir = os.environ['CMSSW_BASE'] + '/src/PandaProd/Producer/cfg'
    lumilist = 'Cert_271036-284044_13TeV_23Sep2016ReReco_Collisions16_JSON.txt'

    if os.path.exists(lumilist):
        options.lumilist = lumilist
    elif os.path.exists(jsonDir + '/' + lumilist):
        options.lumilist = jsonDir + '/' + lumilist
    else:
        print 'No good lumi mask applied'

import FWCore.ParameterSet.Config as cms

process = cms.Process('NTUPLES')
process.schedule = cms.Schedule()

process.load('FWCore.MessageService.MessageLogger_cfi')
process.MessageLogger.cerr.FwkReport.reportEvery = 100
for cat in ['PandaProducer', 'JetPtMismatchAtLowPt', 'JetPtMismatch', 'NullTransverseMomentum', 'MissingJetConstituent']:
    process.MessageLogger.categories.append(cat)
    setattr(process.MessageLogger.cerr, cat, cms.untracked.PSet(limit = cms.untracked.int32(10)))

############
## SOURCE ##
############

### INPUT FILES
process.source = cms.Source('PoolSource',
    skipEvents = cms.untracked.uint32(options.skipEvents),
    fileNames = cms.untracked.vstring(options.inputFiles)
)

### NUMBER OF EVENTS
process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(options.maxEvents)
)

### LUMI MASK
if options.lumilist != '':
    import FWCore.PythonUtilities.LumiList as LumiList
    process.source.lumisToProcess = LumiList.LumiList(filename = options.lumilist).getVLuminosityBlockRange()

##############
## SERVICES ##
##############

process.load('Configuration.Geometry.GeometryIdeal_cff') 
process.load('Configuration.StandardSequences.Services_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')

process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
if options.globaltag == '':
    if options.isData:
        process.GlobalTag.globaltag = '80X_dataRun2_2016SeptRepro_v7'
    else:
        process.GlobalTag.globaltag = '80X_mcRun2_asymptotic_2016_TrancheIV_v8'
else:
    process.GlobalTag.globaltag = options.globaltag

process.RandomNumberGeneratorService.panda = cms.PSet(
    initialSeed = cms.untracked.uint32(1234567),
    engineName = cms.untracked.string('TRandom3')
)
process.RandomNumberGeneratorService.slimmedElectrons = cms.PSet(
    initialSeed = cms.untracked.uint32(89101112),
    engineName = cms.untracked.string('TRandom3')
)
process.RandomNumberGeneratorService.slimmedPhotons = cms.PSet(
    initialSeed = cms.untracked.uint32(13141516),
    engineName = cms.untracked.string('TRandom3')
)

#############################
## RECO SEQUENCE AND SKIMS ##
#############################

import PandaProd.Producer.utils.egmidconf as egmidconf

### EGAMMA CORRECTIONS

from EgammaAnalysis.ElectronTools.regressionApplication_cff import slimmedElectrons as correctedElectrons
from EgammaAnalysis.ElectronTools.regressionApplication_cff import slimmedPhotons as correctedPhotons
from EgammaAnalysis.ElectronTools.regressionWeights_cfi import regressionWeights
regressionWeights(process)
process.correctedElectrons = correctedElectrons
process.correctedPhotons = correctedPhotons

process.selectedElectrons = cms.EDFilter('PATElectronSelector',
    src = cms.InputTag('correctedElectrons'),
    cut = cms.string('pt > 5 && abs(eta) < 2.5')
)

from PandaProd.Producer.utils.calibratedEgamma_cfi import calibratedPatElectrons, calibratedPatPhotons
process.slimmedElectrons = calibratedPatElectrons.clone(
    electrons = 'selectedElectrons',
    isMC = (not options.isData),
    correctionFile = egmidconf.electronSmearingData[egmSmearingType]
)
process.slimmedPhotons = calibratedPatPhotons.clone(
    photons = 'correctedPhotons',
    isMC = (not options.isData),
    correctionFile = egmidconf.photonSmearingData[egmSmearingType]
)   

egmCorrectionSequence = cms.Sequence(
    process.correctedElectrons +
    process.correctedPhotons +
    process.selectedElectrons +
    process.slimmedElectrons +
    process.slimmedPhotons
)

### PUPPI

# 80X does not contain the latest & greatest PuppiPhoton; need to rerun for all config
from PhysicsTools.PatAlgos.slimming.puppiForMET_cff import makePuppiesFromMiniAOD
# Creates process.puppiMETSequence which includes 'puppi' and 'puppiForMET' (= EDProducer('PuppiPhoton'))
# *UGLY* also runs switchOnVIDPhotonIdProducer and sets up photon id Spring16_V2p2 internally
# which loads photonIDValueMapProducer and egmPhotonIDs
makePuppiesFromMiniAOD(process, createScheduledSequence = True)

# Just renaming
puppiSequence = process.puppiMETSequence

### PUPPI JET

from PandaProd.Producer.utils.makeJets_cff import makeJets

puppiJetSequence = makeJets(process, options.isData, 'AK4PFPuppi', 'puppi', 'Puppi')

### PUPPI MET

from PhysicsTools.PatUtils.tools.runMETCorrectionsAndUncertainties import runMetCorAndUncFromMiniAOD
# Creates process.fullPatMetSequencePuppi
# With metType = 'Puppi', slimmedJetsPuppi is automatically selected as the jet source for type 1
runMetCorAndUncFromMiniAOD(
    process,
    isData = options.isData,
    metType = 'Puppi',
    pfCandColl = 'puppiForMET',
    recoMetFromPFCs = True,
    jetFlavor = 'AK4PFPuppi',
    postfix = 'Puppi'
)
# There is a bug in a function used by runMetCorAndUncFromMiniAOD (PhysicsTools.PatAlgos.tools.removeIfInSequence)
# The following module is supposed to be removed from the sequence but is not
# The bug appears when we don't call the no-postfix version of runMetCor.. first
process.fullPatMetSequencePuppi.remove(process.selectedPatJetsForMetT1T2CorrPuppi)

### EGAMMA ID

from PhysicsTools.SelectorUtils.tools.vid_id_tools import setupAllVIDIdsInModule, setupVIDElectronSelection, switchOnVIDElectronIdProducer, DataFormat
# Loads egmGsfElectronIDs
switchOnVIDElectronIdProducer(process, DataFormat.MiniAOD)
setupAllVIDIdsInModule(process, 'RecoEgamma.ElectronIdentification.Identification.cutBasedElectronID_Summer16_80X_V1_cff', setupVIDElectronSelection)
setupAllVIDIdsInModule(process, 'RecoEgamma.ElectronIdentification.Identification.cutBasedElectronHLTPreselecition_Summer16_V1_cff', setupVIDElectronSelection)

# original has @skipCurrentProcess
process.photonIDValueMapProducer.srcMiniAOD = 'slimmedPhotons'

process.load('PandaProd.Auxiliary.WorstIsolationProducer_cfi')

egmIdSequence = cms.Sequence(
    process.photonIDValueMapProducer +
    process.egmPhotonIDs +
    process.egmGsfElectronIDs +
    process.worstIsolationProducer
)

### QG TAGGING

process.load('RecoJets.JetProducers.QGTagger_cfi')
process.QGTagger.srcJets = 'slimmedJets'

### FAT JETS

from PandaProd.Producer.utils.makeFatJets_cff import initFatJets, makeFatJets

# pfCHS set up here
fatJetInitSequence = initFatJets(process, options.isData, ['AK8', 'CA15'])

ak8CHSSequence = makeFatJets(
    process,
    isData = options.isData,
    label = 'AK8PFchs',
    candidates = 'pfCHS'
)

ak8PuppiSequence = makeFatJets(
    process,
    isData = options.isData,
    label = 'AK8PFPuppi',
    candidates = 'puppi'
)

ca15CHSSequence = makeFatJets(
    process,
    isData = options.isData,
    label = 'CA15PFchs',
    candidates = 'pfCHS'
)

ca15PuppiSequence = makeFatJets(
    process,
    isData = options.isData,
    label = 'CA15PFPuppi',
    candidates = 'puppi'
)

from PandaProd.Producer.utils.setupBTag import initBTag, setupDoubleBTag
initBTag(process, '', 'packedPFCandidates', 'offlineSlimmedPrimaryVertices')
ak8CHSDoubleBTagSequence = setupDoubleBTag(process, 'packedPatJetsAK8PFchs', 'AK8PFchs', '', 'ak8')
ak8PuppiDoubleBTagSequence = setupDoubleBTag(process, 'packedPatJetsAK8PFPuppi', 'AK8PFPuppi', '', 'ak8')
ca15CHSDoubleBTagSequence = setupDoubleBTag(process, 'packedPatJetsCA15PFchs', 'CA15PFchs', '', 'ca15')
ca15PuppiDoubleBTagSequence = setupDoubleBTag(process, 'packedPatJetsCA15PFPuppi', 'CA15PFPuppi', '', 'ca15')

fatJetSequence = cms.Sequence(
    fatJetInitSequence +
    ak8CHSSequence +
    ak8PuppiSequence +
    ca15CHSSequence +
    ca15PuppiSequence +
    ak8CHSDoubleBTagSequence +
    ak8PuppiDoubleBTagSequence +
    ca15CHSDoubleBTagSequence +
    ca15PuppiDoubleBTagSequence
)

### GEN JET FLAVORS
if not options.isData:
    process.load('PhysicsTools.JetMCAlgos.HadronAndPartonSelector_cfi')
    from PhysicsTools.JetMCAlgos.AK4PFJetsMCFlavourInfos_cfi import ak4JetFlavourInfos

    process.selectedHadronsAndPartons.particles = 'prunedGenParticles'

    process.ak4GenJetFlavourInfos = ak4JetFlavourInfos.clone(
        jets = 'slimmedGenJets'
    )
    process.ak8GenJetFlavourInfos = ak4JetFlavourInfos.clone(
        jets = 'genJetsNoNuAK8',
        rParam = 0.8
    )
    process.ca15GenJetFlavourInfos = ak4JetFlavourInfos.clone(
        jets = 'genJetsNoNuCA15',
        jetAlgorithm = 'CambridgeAachen',
        rParam = 1.5
    )

    genJetFlavorSequence = cms.Sequence(
        process.selectedHadronsAndPartons +
        process.ak4GenJetFlavourInfos +
        process.ak8GenJetFlavourInfos +
        process.ca15GenJetFlavourInfos
    )
else:
    genJetFlavorSequence = cms.Sequence()

### MONOX FILTER

process.load('PandaProd.Filters.MonoXFilter_cfi')
process.MonoXFilter.taggingMode = True

### RECO PATH

process.reco = cms.Path(
    egmCorrectionSequence +
    egmIdSequence +
    puppiSequence +
    puppiJetSequence +
    process.fullPatMetSequencePuppi +
    process.MonoXFilter +
    process.QGTagger +
    fatJetSequence +
    genJetFlavorSequence
)

if muEGFixed:
    ### RE-EG-CORRECT PUPPI MET

    # THIS FUNCTION IS BUGGY
    # from PhysicsTools.PatUtils.tools.eGammaCorrection import eGammaCorrection
    from PandaProd.Producer.utils.eGammaCorrection import eGammaCorrection

    metCollections = [
        'patPFMetRaw',
        'patPFMetT1',
        'patPFMetT0pcT1',
        'patPFMetT1Smear',
        'patPFMetT1Txy',
        'patPFMetTxy'
    ]
    variations = ['Up', 'Down']
    for var in variations:
        metCollections.extend([
            'patPFMetT1JetEn' + var,
            'patPFMetT1JetRes' + var,
            'patPFMetT1SmearJetRes' + var,
            'patPFMetT1ElectronEn' + var,
            'patPFMetT1PhotonEn' + var,
            'patPFMetT1MuonEn' + var,
            'patPFMetT1TauEn' + var,
            'patPFMetT1UnclusteredEn' + var,
        ])

    # Extracts correction from the differences between pre- and post-GSFix e/g collections
    # and inserts them into various corrected MET objects
    puppiMETEGCorrSequence = eGammaCorrection(
        process, 
        electronCollection = 'slimmedElectronsBeforeGSFix',
        photonCollection = 'slimmedPhotonsBeforeGSFix',
        corElectronCollection = 'slimmedElectrons',
        corPhotonCollection = 'slimmedPhotons',
        metCollections = metCollections,
        pfCandMatching = False,
        pfCandidateCollection = 'packedPFCandidates',
        postfix = 'Puppi'
    )

    process.slimmedMETsPuppi.rawVariation = 'patPFMetRawPuppi'

    # insert right after pat puppi met production
    process.fullPatMetSequencePuppi.insert(process.fullPatMetSequencePuppi.index(process.patMetModuleSequencePuppi) + 1, puppiMETEGCorrSequence)

else:
    ### PF CLEANING (BAD MUON REMOVAL)
   
    # Replace all references made so far to packedPFCandidates with cleanMuonsPFCandidates

    from PhysicsTools.PatAlgos.tools.helpers import MassSearchReplaceAnyInputTagVisitor

    replacePFCandidates = MassSearchReplaceAnyInputTagVisitor('packedPFCandidates', 'cleanMuonsPFCandidates', verbose = False)
    for everywhere in [process.producers, process.filters, process.analyzers, process.psets, process.vpsets]:
        for name, obj in everywhere.iteritems():
            replacePFCandidates.doIt(obj, name)

    from PhysicsTools.PatUtils.tools.muonRecoMitigation import muonRecoMitigation

    # Adds badGlobalMuonTaggerMAOD, cloneGlobalMuonTaggerMAOD, badMuons, and cleanMuonsPFCandidates
    muonRecoMitigation(
        process,
        pfCandCollection = 'packedPFCandidates',
        runOnMiniAOD = True
    )

    # And of course this is against the convention (MET filters are true if event is *good*) but that's what the REMINIAOD developers chose.
    process.Flag_badMuons = cms.Path(process.badGlobalMuonTaggerMAOD)
    process.Flag_duplicateMuons = cms.Path(process.cloneGlobalMuonTaggerMAOD)
    process.schedule += [process.Flag_badMuons, process.Flag_duplicateMuons]

    pfCleaningSequence = cms.Sequence(
        process.badMuons +
        process.cleanMuonsPFCandidates
    )

    process.reco.insert(0, pfCleaningSequence)

if jetMETReco:
    ### JET RE-CORRECTION

    from PhysicsTools.PatAlgos.producersLayer1.jetUpdater_cff import updatedPatJetCorrFactors, updatedPatJets

    jecLevels= ['L1FastJet',  'L2Relative', 'L3Absolute']
    if options.isData:
        jecLevels.append('L2L3Residual')
    
    process.updatedPatJetCorrFactors = updatedPatJetCorrFactors.clone(
        src = cms.InputTag('slimmedJets', '', cms.InputTag.skipCurrentProcess()),
        levels = cms.vstring(*jecLevels),
    )

    process.slimmedJets = updatedPatJets.clone(
        jetSource = cms.InputTag('slimmedJets', '', cms.InputTag.skipCurrentProcess()),
        addJetCorrFactors = cms.bool(True),
        jetCorrFactorsSource = cms.VInputTag(cms.InputTag('updatedPatJetCorrFactors')),
        addBTagInfo = cms.bool(False),
        addDiscriminators = cms.bool(False)
    )

    jetRecorrectionSequence = cms.Sequence(
        process.updatedPatJetCorrFactors +
        process.slimmedJets
    )

    process.reco.insert(process.reco.index(process.QGTagger), jetRecorrectionSequence)

    ### MET
    # Collections naming aligned with 03Feb2017 reminiaod

    # Creates process.fullPatMetSequenceUncorrected which includes slimmedMETsUncorrected
    runMetCorAndUncFromMiniAOD(
        process,
        isData = options.isData,
        postfix = 'Uncorrected'
    )
    # See note on puppi met
    process.fullPatMetSequenceUncorrected.remove(process.selectedPatJetsForMetT1T2CorrUncorrected)

    # Creates process.fullPatMetSequenceMuEGClean which includes slimmedMETsMuEGClean
    # Postfix MuEGClean is just for convenience - there is no EG cleaning actually applied
    runMetCorAndUncFromMiniAOD(
        process,
        isData = options.isData,
        pfCandColl = 'cleanMuonsPFCandidates',
        recoMetFromPFCs = True,
        postfix = 'MuEGClean'
    )
    # See note on puppi met
    process.fullPatMetSequenceMuEGClean.remove(process.selectedPatJetsForMetT1T2CorrMuEGClean)

    process.reco += process.fullPatMetSequenceUncorrected
    process.reco += process.fullPatMetSequenceMuEGClean

# Repeated calls to runMetCorAnd.. overwrites the MET source of patCaloMet
process.patCaloMet.metSource = 'metrawCaloPuppi'

#############
## NTULPES ##
#############

process.load('PandaProd.Producer.panda_cfi')
process.panda.isRealData = options.isData
process.panda.useTrigger = options.useTrigger
#process.panda.SelectEvents = ['reco'] # no skim
if options.isData:
    process.panda.fillers.partons.enabled = False
    process.panda.fillers.genParticles.enabled = False
    process.panda.fillers.ak4GenJets.enabled = False
    process.panda.fillers.ak8GenJets.enabled = False
    process.panda.fillers.ca15GenJets.enabled = False
if not options.useTrigger:
    process.panda.fillers.hlt.enabled = False

process.panda.fillers.pfMet.met = 'slimmedMETsMuEGClean'
process.panda.fillers.metNoFix = process.panda.fillers.puppiMet.clone(
    met = 'slimmedMETsUncorrected'
)
if muEGFixed:
    process.panda.fillers.electrons.gsUnfixedElectrons = cms.untracked.string('slimmedElectronsBeforeGSFix')
    process.panda.fillers.photons.gsUnfixedPhotons = cms.untracked.string('slimmedPhotonsBeforeGSFix')
    process.panda.fillers.metMuOnlyFix = process.panda.fillers.puppiMet.clone(
        met = 'slimmedMETs'
    )
    process.panda.fillers.metFilters.dupECALClusters = cms.untracked.string('particleFlowEGammaGSFixed:dupECALClusters')
    process.panda.fillers.metFilters.unfixedECALHits = cms.untracked.string('ecalMultiAndGSGlobalRecHitEB:hitsNotReplaced')

process.panda.outputFile = options.outputFile
process.panda.printLevel = options.printLevel

process.ntuples = cms.EndPath(process.panda)

process.schedule += [process.reco, process.ntuples]

if options.connect:
    if options.connect == 'mit':
        options.connect = 'frontier://(proxyurl=http://squid.cmsaf.mit.edu:3128)(proxyurl=http://squid1.cmsaf.mit.edu:3128)(proxyurl=http://squid2.cmsaf.mit.edu:3128)(serverurl=http://cmsfrontier.cern.ch:8000/FrontierProd)/CMS_CONDITIONS'

    process.GlobalTag.connect = options.connect
    for toGet in process.GlobalTag.toGet:
        toGet.connect = options.connect
