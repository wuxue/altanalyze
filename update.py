#!/usr/local/bin/python2.6

###update
#Copyright 2005-2008 J. David Gladstone Institutes, San Francisco California
#Author Nathan Salomonis - nsalomonis@gmail.com

#Permission is hereby granted, free of charge, to any person obtaining a copy 
#of this software and associated documentation files (the "Software"), to deal 
#in the Software without restriction, including without limitation the rights 
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
#copies of the Software, and to permit persons to whom the Software is furnished 
#to do so, subject to the following conditions:

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
#INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
#PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
#OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
#SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""This module contains generic methods for downloading and decompressing files designated
online files and coordinating specific database build operations for all AltAnalyze supported
gene ID systems with other program modules. """

import os
import sys
import unique
import string
import export

def filepath(filename):
    fn = unique.filepath(filename)
    return fn

def read_directory(sub_dir):
    dir_list = unique.read_directory(sub_dir); dir_list2 = []
    ###Code to prevent folder names from being included
    for entry in dir_list:
        if entry[-4:] == ".txt" or entry[-4:] == ".csv": dir_list2.append(entry)
    return dir_list2

def cleanUpLine(line):
    line = string.replace(line,'\n','')
    line = string.replace(line,'\c','')
    data = string.replace(line,'\r','')
    data = string.replace(data,'"','')
    return data

def zipDirectory(dir):
    #http://www.testingreflections.com/node/view/8173
    import zipfile
    dir = filepath(dir); zip_file = dir+'.zip'
    p = string.split(dir,'/'); top=p[-1]
    zip = zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED)
    root_len = len(os.path.abspath(dir))
    for root, dirs, files in os.walk(dir):
        archive_root = os.path.abspath(root)[root_len:]
        for f in files:
            fullpath = os.path.join(root, f)
            archive_name = os.path.join(top+archive_root, f)
            zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)
    zip.close()
    return zip_file

def unzipFiles(filename,dir):
    import zipfile
    output_filepath = filepath(dir+filename)
    try:
        zfile = zipfile.ZipFile(output_filepath)
        for name in zfile.namelist():
            if name.endswith('/'):null=[] ### Don't need to export
            else: 
                try: outfile = export.ExportFile(dir+name)
                except Exception: outfile = export.ExportFile(dir+name[1:])
                outfile.write(zfile.read(name)); outfile.close()
        #print 'Zip extracted to:',output_filepath
        status = 'completed'
    except Exception, e:
        print e
        print 'WARNING!!!! The zip file',output_filepath,'does not appear to be a valid zip archive file or is currupt.'
        status = 'failed'
    return status

############## Update Databases ##############
def buildJunctionExonAnnotations(species,array_type,force,genomic_build):
    ### Get UCSC associations (download databases if necessary)
    import UCSCImport
    mRNA_Type = 'mrna'; run_from_scratch = 'yes'; force='no'
    export_all_associations = 'no' ### YES only for protein prediction analysis
    UCSCImport.runUCSCEnsemblAssociations(species,mRNA_Type,export_all_associations,run_from_scratch,force)

    ### Get genomic locations and initial annotations for exon sequences (exon pobesets and junctions)    
    import JunctionArray
    import JunctionArrayEnsemblRules
    """ The following functions:
    1) Extract transcript cluster-to-gene annotations
    2) Extract exon sequences for junctions and exon probesets from the Affymetrix annotation file (version 2.0),
    3) Map these sequences to Ensembl gene sequences (build specific) plus and minus 2KB, upstream and downstream
    4) Obtain AltAnalyze exon region annotations and obtain full-length exon sequences for each exon probeset
    5) Consoladate these into an Ensembl_probeset.txt file (rather than Ensembl_junction_probeset.txt) with junctions
       having a single probeset identifier.
    6) Determine which junctions and junction-exons represent recipricol junctions using:
       a) AltAnalyze identified recipricol junctions from Ensembl and UCSC and
       b) Affymetrix suggested recipricol junctions based on common exon cluster annotations, creating
          Mm_junction_comps_updated.txt.
       c) De novo comparison of all exon-junction region IDs for all junctions using the EnsemblImport method compareJunctions().
    """
    ### Steps 1-3
    JunctionArray.getJunctionExonLocations(species,array_type)
    ### Step 4
    JunctionArrayEnsemblRules.getAnnotations(species,array_type,'yes',force)
    ### Step 5-6
    JunctionArray.identifyJunctionComps(species,array_type)
    
    
def buildAltMouseExonAnnotations(species,array_type,force,genomic_build):
    """Code required to:
    1) Extract out Affymetrix provided exon sequence (probeset sequence extracted from "probeset_sequence_reversed.txt", derived
       directly from the Affymetrix AltMouse probe annotation file), from the "SEQUENCE-transcript-dbase.txt" (built using
       dump-chip1 .gff sequence and AltMerge-Peptide Informatics script "sequence_analysis_AltMouse_refseq.py").
    2) Once exported, grab full length exon sequences using exon/intron coordinates matches to full-length gene sequences with 2kb
       flanking sequence to efficiently predict microRNA binding site exclusion (reAnnotateCriticalExonSequences) and later for
       coordinate mapping to get exons aligning with UCSC annotated splicing annotations and exons. This sequence data replaced
       the previous file (don't need to re-run this - see rederive_exonseq == 'yes' below for reference).
    3) Match the updated exon sequences to the most recent genomic coordinates and build the exact equivalent of the exon array
       Mm_Ensembl_probeset.txt database (same structure and ExonArrayEnsemblRules.py code). This involves running EnsemblImport.
    This code should be run before the exon array location build code since the "Mm_Ensembl_probeset.txt" is created and then re-
    written as "Mm_AltMouse_Ensembl_probeset.txt".
    """
    
    import JunctionArray
    import JunctionArrayEnsemblRules    
    rederive_exonseq = 'no'
    ### Only needs to be run once, to export exon sequence for AltMouse array the original (1 and 2 above)
    if rederive_exonseq == 'yes':
        import AltAnalyze
        import ExonAnnotate_module
        import ExonAnalyze_module
        agglomerate_inclusion_probesets = 'no'; onlyAnalyzeJunctions='no'
        probeset_annotations_file = "AltDatabase/"+species+"/"+array_type+"/"+"MASTER-probeset-transcript.txt"
        exon_db={}; filtered_arrayids={};filter_status='no'
        constituitive_probeset_db,exon_db,genes_being_analyzed = AltAnalyze.importSplicingAnnotationDatabase(probeset_annotations_file,array_type,filtered_arrayids,filter_status)
        alt_junction_db,critical_exon_db,exon_dbase,exon_inclusion_db,exon_db = ExonAnnotate_module.identify_putative_splice_events(exon_db,constituitive_probeset_db,{},agglomerate_inclusion_probesets,onlyAnalyzeJunctions)
        ExonAnnotate_module.exportJunctionComparisons(alt_junction_db,critical_exon_db,exon_dbase)
        print "Finished exporting junctions used in AltMouse array comparisons."

        ExonAnalyze_module.exportAltMouseExonSequence()
        JunctionArray.reAnnotateCriticalExonSequences(species,array_type)

    ### Get UCSC associations (download databases if necessary)
    import UCSCImport
    mRNA_Type = 'mrna'; run_from_scratch = 'yes'
    export_all_associations = 'no' ### YES only for protein prediction analysis
    UCSCImport.runUCSCEnsemblAssociations(species,mRNA_Type,export_all_associations,run_from_scratch,force)

    reannotate_exon_seq = 'yes'
    print 'genomic_build', genomic_build
    if genomic_build == 'new':
        ### Need to run with every new genomic build (match up new coordinates
        print "Begining to derive exon sequence from new genomic build"
        JunctionArray.identifyCriticalExonLocations(species,array_type)
        reannotate_exon_seq = 'yes'
    JunctionArrayEnsemblRules.getAnnotations(species,array_type,reannotate_exon_seq,force)

def buildExonArrayExonAnnotations(species, array_type, force):

    ### Get UCSC associations (download databases if necessary)
    import UCSCImport
    mRNA_Type = 'mrna'; run_from_scratch = 'yes'
    export_all_associations = 'no' ### YES only for protein prediction analysis
    UCSCImport.runUCSCEnsemblAssociations(species,mRNA_Type,export_all_associations,run_from_scratch,force)
    
    import ExonArrayEnsemblRules; reload(ExonArrayEnsemblRules)
    process_from_scratch='yes'
    constitutive_source='default'
    ### Build the databases and return the variables (not used here)
    source_biotype = 'mRNA'
    if array_type == 'gene': source_biotype = 'gene'
    probeset_db,annotate_db,constitutive_gene_db,splicing_analysis_db = ExonArrayEnsemblRules.getAnnotations(process_from_scratch,constitutive_source,source_biotype,species)

def buildUniProtFunctAnnotations(species,force):
    import UI
    file_location_defaults = UI.importDefaultFileLocations()
    """Identify the appropriate download location for the UniProt database for the selected species"""
    uis = file_location_defaults['UniProt']
    tis = file_location_defaults['TrEMBL']
    
    for ui in uis:
        if species in ui.Species(): uniprot_filename_url = ui.Location()
    for ti in tis:
        if species in ti.Species(): trembl_filename_url = ti.Location()
    species_codes = importSpeciesInfo(); species_full = species_codes[species].SpeciesName()
    
    import ExtractUniProtFunctAnnot; reload(ExtractUniProtFunctAnnot)
    ExtractUniProtFunctAnnot.runExtractUniProt(species,species_full,uniprot_filename_url,trembl_filename_url,force)

class SpeciesData:
    def __init__(self, abrev, species):
        self._abrev = abrev; self._species = species
    def SpeciesCode(self): return self._abrev
    def SpeciesName(self): return self._species
    def __repr__(self): return self.Report()
    
def importSpeciesInfo():
    filename = 'Config/species.txt'; x=0
    fn=filepath(filename); species_codes={}
    for line in open(fn,'rU').readlines():             
        data = cleanUpLine(line)
        abrev,species,algorithms = string.split(data,'\t')
        if x==0: x=1
        else:
            sd = SpeciesData(abrev,species)
            species_codes[abrev] = sd
    return species_codes
    
def download(url,dir,file_type):
    try: dp = download_protocol(url,dir,file_type); output_filepath, status  = dp.getStatus(); fp = output_filepath
    except Exception:
        output_filepath='failed'; status = "Internet connection not established. Re-establish and try again."
        fp = filepath(dir+url.split('/')[-1]) ### Remove this empty object if saved

    if '.zip' in fp or '.gz' in fp or '.tar' in fp:
        #print "\nRemoving zip file:",fp
        try: os.remove(fp); status = 'removed'
        except Exception: null=[] ### Not sure why this error occurs since the file is not open
    return output_filepath, status

class download_protocol:
    def __init__(self,url,dir,file_type):
        """Copy the contents of a file from a given URL to a local file."""
        filename = url.split('/')[-1]; self.status = ''
        if file_type == None: file_type =''
        if len(file_type) == 2: filename, file_type = file_type ### Added this feature for when a file has an invalid filename
        output_filepath_object = export.createExportFile(dir+filename,dir[:-1])
        output_filepath = filepath(dir+filename); self.output_filepath = output_filepath
        
        print "Downloading the following file:",filename,' ',
        #print "outputpath:",output_filepath
        #print url
        self.original_increment = 5
        self.increment = 0
        from urllib import urlretrieve
        webfile, msg = urlretrieve(url, output_filepath,reporthook=self.reporthookFunction)
        print ''; self.testFile()
        print self.status
        if 'Internet' not in self.status:
            if '.zip' in filename:
                print "Extracting zip file...",
                try: decompressZipStackOverflow(filename,dir); status = 'completed'
                except Exception:
                    status = unzipFiles(filename,dir)
                    if status == 'failed': print 'zip extraction failed!'
                self.gz_filepath = filepath(output_filepath); self.status = 'remove'
                print "zip file extracted"
            elif '.gz' in filename:
                self.gz_filepath = output_filepath
                if len(file_type)==0: extension = '.gz'
                else: extension = 'gz'
                decompressed_filepath = string.replace(self.gz_filepath,extension,file_type)
                ### Below code can be too memory intensive
                #file_size = os.path.getsize(output_filepath)
                #megabtyes = file_size/1000000.00
                #if megabtyes>5000: force_error ### force_error is an undefined variable which causes an exception
                import gzip; content = gzip.GzipFile(self.gz_filepath, 'rb')
                data = open(decompressed_filepath,'wb')
                #print "\nExtracting downloaded file:",self.gz_filepath
                import shutil; shutil.copyfileobj(content,data)
                self.status = 'remove'
            else: self.gz_filepath = ''; self.status = 'remove'
    def testFile(self):
        fn=filepath(self.output_filepath)
        try:
            for line in open(fn,'rU').xreadlines():
                if '!DOCTYPE' in line: self.status = "Internet connection not established. Re-establish and try again."
                break
        except Exception: null=[]
        
    def getStatus(self): return self.output_filepath, self.status
    def reporthookFunction(self, blocks_read, block_size, total_size):
        if not blocks_read:
            print 'Connection opened. Downloading (be patient)'
        if total_size < 0:
            # Unknown size
            print 'Read %d blocks' % blocks_read
        else:
            amount_read = blocks_read * block_size
            percent_read = ((amount_read)*1.00/total_size)*100
            if percent_read>self.increment:
                #print '%d%% downloaded' % self.increment
                print '*',
                self.increment += self.original_increment
            #print 'Read %d blocks, or %d/%d' % (blocks_read, amount_read, (amount_read/total_size)*100.000)

def createExportFile(new_file,dir):
    try:
        fn=filepath(new_file); file_var = open(fn,'w')
    except IOError:
        #print "IOError", fn
        fn = filepath(dir)
        try:
            os.mkdir(fn) ###Re-Create directory if deleted
            #print fn, 'written'
        except OSError: createExportDir(new_file,dir) ###Occurs if the parent directory is also missing
        fn=filepath(new_file); file_var = open(fn,'w')
    return file_var

def downloadCurrentVersionUI(filename,secondary_dir,file_type,root):
    continue_analysis = downloadCurrentVersion(filename,secondary_dir,file_type)
    if continue_analysis == 'no':
        import UI
        try: root.destroy(); UI.getUserParameters('no'); sys.exit()
        except Exception: sys.exit()
    try: root.destroy()
    except Exception(): null=[] ### Occurs when running from command-line
        
def downloadCurrentVersion(filename,secondary_dir,file_type):
    import UI
    file_location_defaults = UI.importDefaultFileLocations()

    ud = file_location_defaults['url'] ### Get the location of the download site from Config/default-files.csv
    url_dir = ud.Location() ### Only one entry
    
    dir = export.findParentDir(filename)  
    filename = export.findFilename(filename)
    url = url_dir+secondary_dir+'/'+filename

    file,status = download(url,dir,file_type); continue_analysis = 'yes'
    if 'Internet' in status:
        print_out = "File:\n"+url+"\ncould not be found on server or internet connection is unavailable."
        try:
            UI.WarningWindow(print_out,'WARNING!!!')
            continue_analysis = 'no'
        except Exception:
            print url
            print 'cannot be downloaded';die
    elif status == 'remove' and ('.zip' in file or '.tar' in file or '.gz' in file):
        try: os.remove(file) ### Not sure why this works now and not before
        except Exception: status = status
    return continue_analysis

def decompressZipStackOverflow(zip_file,dir):
    zip_file = filepath(dir+zip_file)
    ###http://stackoverflow.com/questions/339053/how-do-you-unzip-very-large-files-in-python
    import zipfile
    import zlib
    src = open(zip_file,"rb")
    zf = zipfile.ZipFile(src)
    for m in zf.infolist():
        # Examine the header
        #print m.filename, m.header_offset, m.compress_size, repr(m.extra), repr(m.comment)
        src.seek(m.header_offset)
        src.read(30) # Good to use struct to unpack this.
        nm= src.read(len(m.filename))
        if len(m.extra) > 0: ex= src.read(len(m.extra))
        if len(m.comment) > 0: cm=src.read(len(m.comment)) 

        # Build a decompression object
        decomp= zlib.decompressobj(-15)

        # This can be done with a loop reading blocks
        out=open(filepath(dir+m.filename), "wb")
        result=decomp.decompress(src.read(m.compress_size))
        out.write(result); result=decomp.flush()
        out.write(result); out.close()
    zf.close()
    src.close()
    
def updateDBs(species,array_type):
    update_uniprot='no'; update_ensembl='no'; update_probeset_to_ensembl='no'; update_domain='no'; update_all='no'; update_miRs='no'
    proceed = 'no'; genomic_build = 'old'

    while proceed == 'no':
        print "\n*****Select Species*****"
        print "1) Human"
        print "2) Mouse"
        print "3) Rat"
        print "4) all"
        print "5) Quit"
        inp = sys.stdin.readline(); inp = inp.strip()
        if inp  == '1': species = ['Hs']; proceed = 'yes'
        elif inp == '2': species = ['Mm']; proceed = 'yes'
        elif inp == '3': species = ['Rn']; proceed = 'yes'
        elif inp == '4': species = ['Mm','Hs','Rn']; proceed = 'yes'
        elif inp == '5': sys.exit()
        else: print "Sorry... that command is not an option\n"  

    proceed = 'no'
    while proceed == 'no':
        print "\n*****Select Array Type*****"
        print "1) Exon"
        print "2) Gene"
        print "3) AltMouse"
        print "4) all"
        print "5) Quit"
        inp = sys.stdin.readline(); inp = inp.strip()
        if inp  == '1': array_type = ['exon']; proceed = 'yes'
        elif inp == '2': array_type = ['gene']; proceed = 'yes'
        elif inp == '3': array_type = ['AltMouse']; proceed = 'yes'
        elif inp == '4': array_type = ['AltMouse','gene','exon']; proceed = 'yes'
        elif inp == '5': sys.exit()
        else: print "Sorry... that command is not an option\n"

    proceed = 'no'        
    while proceed == 'no':
        print "\n*****Update AltAnalyze Database Options***** \n"
        print "Program Options: Updates for species",species,"and array type",array_type
        print "NOTE: some files will needed be manually updated before continuing (e.g., Affymetrix and Ensembl files). See ReadMe for more info."
        print "1) Update UniProt"
        print "2) Update Ensembl"
        print "3) Update Probeset-Ensembl associations"
        print "4) Update Protein/Domain associations"
        print "5) Update miRNA aligments"
        print "6) Update All"
        print "7) Quit"
        inp = sys.stdin.readline(); inp = inp.strip()
        if inp  == '1': update_uniprot = 'yes'; proceed = 'yes'
        elif inp == '2': update_ensembl = 'yes'; proceed = 'yes'
        elif inp == '3': update_probeset_to_ensembl = 'yes'; proceed = 'yes'
        elif inp == '4': update_domain = 'yes'; proceed = 'yes'
        elif inp == '5': update_miRs = 'yes'; proceed = 'yes'
        elif inp == '6': update_all = 'yes'; proceed = 'yes'
        elif inp == '7': sys.exit()
        else: print "Sorry... that command is not an option\n"

    proceed = 'no'
    while proceed == 'no':
        print "\n*****Update AltAnalyze Database Options*****"
        print "1) Force download of all files (whether present locally or not) "
        print "2) Use local or download if necessary"
        print "3) Quit"
        inp = sys.stdin.readline(); inp = inp.strip()
        if inp  == '1': force = 'yes'; proceed = 'yes'
        elif inp == '2': force = 'no'; proceed = 'yes'
        elif inp == '3': sys.exit()
        else: print "Sorry... that command is not an option\n"        

    if 'AltMouse' in array_type:
        proceed = 'no'
        while proceed == 'no':
            print "\n*****Update AltAnalyze Database Options*****"
            print "1) New genomic build."
            print "2) Genomic build is identical to prior database build."
            print "3) Quit"
            inp = sys.stdin.readline(); inp = inp.strip()
            if inp  == '1': genomic_build = 'new'; proceed = 'yes'
            elif inp == '2': genomic_build = 'old'; proceed = 'yes'
            elif inp == '3': sys.exit()
            else: print "Sorry... that command is not an option\n"
            
    for specific_species in species:
        for specific_array_type in array_type:
            if specific_array_type == 'AltMouse' and specific_species == 'Mm': proceed = 'yes'
            elif specific_array_type == 'exon' or specific_array_type == 'gene': proceed = 'yes'
            else: proceed = 'no'
            if proceed == 'yes':
                print "Analyzing", specific_species, specific_array_type
                executeParameters(specific_species,specific_array_type,force,genomic_build,update_uniprot,update_ensembl,update_probeset_to_ensembl,update_domain,update_miRs,update_all)
    
def executeParameters(species,array_type,force,genomic_build,update_uniprot,update_ensembl,update_probeset_to_ensembl,update_domain,update_miRs,update_all,update_miR_seq,ensembl_version):    
    if update_all == 'yes':
        update_uniprot='yes'; update_ensembl='yes'; update_probeset_to_ensembl='yes'; update_domain='yes'; update_miRs = 'yes'
        
    if update_ensembl == 'yes':
        import EnsemblSQL; reload(EnsemblSQL)

        """ Used to grab all essential Ensembl annotations previously obtained via BioMart"""        
        configType = 'Advanced'; analysisType = 'AltAnalyzeDBs'; externalDBName = ''
        EnsemblSQL.buildEnsemblRelationalTablesFromSQL(species,configType,analysisType,externalDBName,ensembl_version,force)
        
        """ Used to grab Ensembl-to-External gene associations"""
        configType = 'Basic'; analysisType = 'ExternalOnly'; externalDBName = 'Uniprot/SWISSPROT'
        EnsemblSQL.buildEnsemblRelationalTablesFromSQL(species,configType,analysisType,externalDBName,ensembl_version,force)
        
        """ Used to grab Ensembl full gene sequence plus promoter and 3'UTRs """
        if array_type == 'AltMouse' or array_type == 'junction':
            EnsemblSQL.getFullGeneSequences(ensembl_version,species)
            
    if update_uniprot == 'yes':            
        ###Might need to delete the existing versions of downloaded databases or force download
        buildUniProtFunctAnnotations(species,force)
                
    if update_probeset_to_ensembl == 'yes':
        if species == 'Mm' and array_type == 'AltMouse':
            buildAltMouseExonAnnotations(species,array_type,force,genomic_build)
        elif array_type == 'junction':
            buildJunctionExonAnnotations(species,array_type,force,genomic_build)
        elif array_type == 'RNASeq':
            import RNASeq; test_status = 'no'; data_type = 'mRNA'
            RNASeq.getEnsemblAssociations(species,data_type,test_status,force)
        else: buildExonArrayExonAnnotations(species,array_type,force)

    if update_domain == 'yes':

        ### Get UCSC associations for all Ensembl linked genes (download databases if necessary)        if species == 'Mm' and array_type == 'AltMouse':
        import UCSCImport
        mRNA_Type = 'mrna'; run_from_scratch = 'yes'
        export_all_associations = 'yes' ### YES only for protein prediction analysis
        UCSCImport.runUCSCEnsemblAssociations(species,mRNA_Type,export_all_associations,run_from_scratch,force)        

        if (species == 'Mm' and array_type == 'AltMouse'):
            """Imports and re-exports array-Ensembl annotations"""
            import JunctionArray
            null = JunctionArray.importArrayAnnotations(species,array_type); null={}
        if (species == 'Mm' and array_type == 'AltMouse') or array_type == 'junction' or array_type == 'RNASeq':
            """Performs probeset sequence aligment to Ensembl and UCSC transcripts. To do: Need to setup download if files missing"""
            import mRNASeqAlign
            mRNASeqAlign.alignProbesetsToTranscripts(species,array_type,force)
       
        import IdentifyAltIsoforms; run_seqcomp = 'no'
        IdentifyAltIsoforms.runProgram(species,array_type,'null',force,run_seqcomp)
        import FeatureAlignment
        FeatureAlignment.findDomainsByGenomeCoordinates(species,array_type,'null')
        
        if array_type == 'junction' or array_type == 'RNASeq':
            IdentifyAltIsoforms.runProgram(species,array_type,'exon',force,run_seqcomp)
            ### FeatureAlignment.findDomainsByGenomeCoordinates(species,array_type,'exon') # not needed
            
    if update_miRs == 'yes':
        if update_miR_seq == 'yes':
            import MatchMiRTargetPredictions; only_add_sequence_to_previous_results = 'no'
            MatchMiRTargetPredictions.runProgram(species,force,only_add_sequence_to_previous_results)

        if array_type == 'exon' or array_type == 'gene':        
            import ExonSeqModule
            stringency = 'strict'; process_microRNA_predictions = 'yes'; mir_source = 'multiple'
            ExonSeqModule.runProgram(species,array_type,process_microRNA_predictions,mir_source,stringency)
            stringency = 'lax'
            ExonSeqModule.runProgram(species,array_type,process_microRNA_predictions,mir_source,stringency)
            filename = 'AltDatabase/'+species+'/SequenceData/miRBS-combined_gene-targets.txt'; ef=filepath(filename)
            er = string.replace(ef,species+'/SequenceData/miRBS-combined_gene-targets.txt','ensembl/'+species+'/'+species+'_microRNA-Ensembl.txt')
            import shutil; shutil.copyfile(ef,er)
            import ExonArray
            ExonArray.exportMetaProbesets(array_type,species) ### Export metaprobesets for this build
        else:
            import JunctionSeqModule
            stringency = 'strict'; mir_source = 'multiple'
            JunctionSeqModule.runProgram(species,array_type,mir_source,stringency,force)
            stringency = 'lax'
            JunctionSeqModule.runProgram(species,array_type,mir_source,stringency,force)

    if array_type == 'junction':
        import JunctionArray; import JunctionArrayEnsemblRules
        JunctionArray.filterForCriticalExons(species,array_type)
        JunctionArrayEnsemblRules.annotateJunctionIDsAsExon(species,array_type)
        
if __name__ == '__main__':
    #zipDirectory('Rn/EnsMart49');kill
    #unzipFiles('Rn.zip', 'AltDatabaseNoVersion/');kill    
    #filename = 'http://altanalyze.org/archiveDBs/LibraryFiles/Mouse430_2.zip'
    #filename = 'AltDatabase/affymetrix/LibraryFiles/Mouse430_2.zip'
    #downloadCurrentVersionUI(filename,'LibraryFiles','','')
    #dp = download_protocol('http://genmapp.org/go_elite/Databases/EnsMart56/Dr.zip','Databases','')
    #kill
    #target_folder = 'Databases/Ci'; zipDirectory(target_folder)
    #unzipFiles('Cs.zip', 'Databases/');kill
    #buildUniProtFunctAnnotations('Hs',force='no')
    """import UI
    date = UI.TimeStamp(); file_type = ('wikipathways_'+date+'.tab','.txt')
    url  ='http://www.wikipathways.org/wpi/pathway_content_flatfile.php?output=tab'
    output = 'BuildDBs/wikipathways/'
    file_type = ''
    url = 'http://www.genmapp.org/go_elite/Databases/EnsMart56/Cs.zip'
    output = 'Databases/'
    fln,status = download(url,output,file_type)
    print status;kill
        
    url='http://altanalyze.org/archiveDBs/LibraryFiles/MoEx-1_0-st-v1.r2.antigenomic.bgp.gz'
    dir='AltDatabase/affymetrix/LibraryFiles/'
    file_type = ''
    download(url,dir,file_type)"""
    
    species='Hs'; array_type = 'junction'
    #updateDBs(species,array_type); sys.exit()
    #"""
    array_type = ['RNASeq']; species = ['Mm']; force = 'yes'; ensembl_version = '60'
    update_uniprot='no'; update_ensembl='no'; update_probeset_to_ensembl='yes'; update_domain='yes'; update_all='no'; update_miRs='yes'
    proceed = 'yes'; genomic_build = 'old'; update_miR_seq = 'yes'

    for specific_species in species:
        for specific_array_type in array_type:
            if specific_array_type == 'AltMouse' and specific_species == 'Mm': proceed = 'yes'
            elif specific_array_type == 'exon' or specific_array_type == 'gene' or specific_array_type == 'junction': proceed = 'yes'
            else: proceed = 'no'
            if proceed == 'yes':
                print "Analyzing", specific_species, specific_array_type
                executeParameters(specific_species,specific_array_type,force,genomic_build,update_uniprot,update_ensembl,update_probeset_to_ensembl,update_domain,update_miRs,update_all,update_miR_seq,ensembl_version)

    #"""    
