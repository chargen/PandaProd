#!/bin/bash

# Use PandaProd/Producer/scripts/cms-git-diff to find out which packages should be checked out from each branch.

INSTALL=$CMSSW_BASE/src/PandaProd/Producer/scripts/install-pkg

$INSTALL cms-met METRecipe_8020 RecoMET/METFilters PhysicsTools/PatAlgos PhysicsTools/PatUtils RecoMET/METAlgorithms #CommonTools/PileupAlgos
# TEMPORARY UNTIL cms-met pulls this branch
$INSTALL yiiyama puppiphoton_filteredpf CommonTools/PileupAlgos
$INSTALL ikrav egm_id_80X_v3_photons PhysicsTools/SelectorUtils RecoEgamma/PhotonIdentification RecoEgamma/EgammaIsolationAlgos
$INSTALL cms-met METRecipe_80X_part2 CommonTools/PileupAlgos DataFormats/PatCandidates PhysicsTools/PatAlgos PhysicsTools/PatUtils RecoMET/METAlgorithms RecoMET/METFilters # RecoMET/METProducers  # should uncomment if rerun MC

