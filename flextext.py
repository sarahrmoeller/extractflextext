#!/usr/bin/env python
# coding: utf-8

# In[12]:


import xml.etree.ElementTree as ET # parses XML files
import string
import os


# # Extract Data from flextext XML files

# In[13]:


# placeholders/delimiters
TEMP = '@@@'

# text-level flextext XML attributes
TITLE_TYPE = 'title'
COMMENT_TYPE = 'comment'
# flextext XML attributes for languages/scripts used in title or translations
ENGLISH = 'en'
INDONESIAN = 'id'

# IGT tier-level flextext XML attributes
TXT = 'txt' # surface morph/segment AND transcribed text
CAN_MORPHEME = 'cf' # canonical (underlying) morpheme
GLOSS = 'gls' # morpheme gloss AND sentence free translation
M_POS = 'msa' # morpheme-level pos, what category affix attaches to
WORD_POS = 'pos' # word-level pos
PUNCT = 'punct' # punctuation

# morpheme types (flextext XML attributes)
MWE = 'phrase' # multiword expression
PREFIX = 'prefix'
SUFFIX = 'suffix'
CIRCUMFIX = 'circumfix'
PROCLITIC = 'proclitic'
ENCLITICS = ['enclitic', 'clitic'] # NOTE: clitic functions as enclitic in some FLEx databases (e.g. lmk)
INFIXES = ['infix', 'infixing interfix']
STEMS = ['stem', 'bound stem', 'bound root', 'bound root A', 'root', 'particle']    

# Segment boundaries are  uniquely marked in FLEx, add yours here
# NOTE: FLEx databases handle circumfixes differently
# NOTE: these symbols will need to be removed before re-importing to FLEx
CIRCUM_PRE = '>'
CIRCUM_POST = '<'
CIRCUM_HOLE = '<>'
CLITIC = '='


# In[14]:


def getTitleComment(xmlsection):
    '''find title and comment if in this section
    some documents have both and english and native language titles
    these checks assure that the both will always be used if found separated by //
    if only one of them is found then it is used
    if none are found return NO TITLE FOUND'''
    
    title = "NO TITLE FOUND" 
    eng_title = TEMP
    non_eng_title = TEMP
    comment = "No comment"
    
    for item_lin in xmlsection.iter('item'):
        if item_lin.get('type') == TITLE_TYPE and item_lin.get('lang') == ENGLISH:
            eng_title = item_lin.text
        if item_lin.get('type') == TITLE_TYPE and item_lin.get('lang') != ENGLISH:
            non_eng_title = item_lin.text
        if item_lin.get('type') == COMMENT_TYPE and item_lin.get('lang') == ENGLISH:
            comment = item_lin.text
    # check languages of title and add either or both
    if eng_title != TEMP and non_eng_title == TEMP:
        title = eng_title 
    elif eng_title == TEMP and non_eng_title != TEMP:
        title = non_eng_title
    elif eng_title != TEMP and non_eng_title != TEMP:
        title = eng_title + ' // ' + non_eng_title 
        
    return title, comment


# In[15]:


# These cleaning functions handle pecularities or non-conventional annotation of IGT

def cleanWord(IGTstring):
    '''formats word to reduce confusion'''
    
    #TODO: reverse before reimporting to FLEx
    
    IGTstring = str(IGTstring)
    
    # TODO?: phrasal lexemes separated by double tilde
    #IGTstring = IGTstring.strip().replace(' ', '~~')
    # use tilde for hyphenated words
    IGTstring = IGTstring.replace('-', '~')
    
    return IGTstring.strip().lower()
    
    
def cleanMorph(IGTstring):
    '''remove unexpected symbols in surface morphs and canonical morphemes
    (includes infixes and circumfix halves)'''
    
    #TODO: reverse before reimporting to FLEx
    
    # separate multiple words in morpheme string with period
    IGTstring = IGTstring.replace(' ', '.')
    
    IGTstring = IGTstring.lower()
    
    # make null morpheme symbol consistent across databases, avoid encoding bugs
    IGTstring = IGTstring.replace('Ø','NULL').replace('∅', 'NULL').replace('zero', 'NULL')
    # add your null morpheme symbol here
    IGTstring = IGTstring.replace('*0','NULL') # lez
    
    # NOTE: add here any pre-processing specific to a database
    #IGTstring = IGTstring.replace('*', '') # NTU
    
    return IGTstring.strip()


def cleanGloss(IGTstring, morpheme_type):
    '''preprocess morpheme glosses
    Follow Leipzig glossing rules where possible'''
    
    # separate multiple words in glosses with period, per linguistic convention
    IGTstring = IGTstring.replace('-','.').replace(' ', '.')
    
    # make affix glosses all caps, per linguistic convention
    if morpheme_type not in STEMS:
        IGTstring = IGTstring.upper()
    
    return IGTstring.strip()


def cleanPOS(IGTstring):
    '''preprocess morpheme-level POS and word-level POS'''
    
    #TODO: reverse before returning to FLEx
    
    # separate multiple tags with period, per linguistic convention
    IGTstring = IGTstring.replace(' ', '')
    # remove FLEx-inserted hyphens, to reduce confusion w morpheme delimiter
    #TODO: reverse before returning to FLEx
    IGTstring = IGTstring.replace('pro-form', 'proform').replace('Nom-1','Nom1')
    
    # NOTE: add here any pre-processing specific to a database
    IGTstring = IGTstring.replace('N (kx cl)', 'N(kx.cl)') ## Natugu [ntu] morpheme pos
    
    return IGTstring.strip()   
    


# In[16]:


def getInfixedStem(wordtxt, morphitem, infix):
    '''infixed stems need special processing,
    especially for non-neural models that require glosses for every segment'''
    
    pre_temp_morph = [TEMP, TEMP, TEMP, TEMP]
    post_temp_morph = [TEMP, TEMP, TEMP, TEMP]
    
    infix = infix[0][1:-1] # remove dashes surrounding infixes
    stemhalves = wordtxt.split(infix) # treat strings surrounding infixes as stems
    
    # get other tiers
    for item in morphitem.iter('item'):
        if item.get('type') != None or item.text != '' or item.text != '<NotSure>' or item.text != ' ':
            # get surface morph, treat same as stem halves
            if (item.get('type') == TXT):
                pre_temp_morph[0] = cleanGloss(stemhalves[0])
                post_temp_morph[0] = cleanGloss(stemhalves[1])
            # canonical morpheme, will be nothing for first half if infixed
            elif(item.get('type') == CAN_MORPHEME):
                pre_temp_morph[1] = cleanMorph(item.text)
                post_temp_morph[1] = cleanMorph(item.text)
            # gloss, same for both
            elif(item.get('type') == GLOSS):
                # separate multi-word glosses with "."
                pre_temp_morph[2] = cleanGloss(item.text)
                post_temp_morph[2] = cleanGloss(item.text)
            # morpheme pos
            elif(item.get('type') == M_POS):
                pre_temp_morph[3] = cleanPOS(item.text)
                post_temp_morph[3] = cleanPOS(item.text)
        else:
            continue
    
    return pre_temp_morph, post_temp_morph


# In[17]:


def getMorpheme(morphitem, morphemetype):
    '''OUTPUT for each morpheme segment: [morph, morpheme, gloss, mpos]
    To add more items to this array of info about morpheme segments:
    1st. Add another holding place in the morph_info array; give index for that info piece.
    2nd. Add elif statement for new tier using the attribute you want, e.g. 'morpheme type'.
        If necessary, create special delimiter and write "cleaning" function.
    3rd. Check that that morph_info array matches entries in temp_morph
        and does not mess up punctuation processing.'''
    
    # temporary array for morpheme information
    morph_info = [TEMP, TEMP, TEMP, TEMP]
    # indexes for types of information to be in morph_info
    MORPH_IDX = 0
    MORPHEME_IDX = 1
    GLOSS_IDX = 2
    M_POS_IDX = 3
    
    # make uniform label for all stem-like morphemes
    # assume missing morpheme type attribute is a stem
    if morphemetype == None or morphemetype in STEMS:
        morphemetype = 'stem'        
    
    # catch "new" morpheme types in current database
    if (morphemetype not in STEMS and morphemetype not in INFIXES
        and morphemetype != PROCLITIC and morphemetype not in ENCLITICS
        and morphemetype != PREFIX and morphemetype != SUFFIX
        and morphemetype != MWE and morphemetype != CIRCUMFIX):
            print("\nThis morpheme type XML attribute is not handled yet in getMorpheme(): " + morphemetype)
    
    # extract information about morpheme from IGT tiers
    for item in morphitem.iter('item'):
        if item.text != None:
            # surface morph (txt)
            if (item.get('type') == TXT):
                if morphemetype in ENCLITICS:
                    morph_info[MORPH_IDX] = CLITIC + cleanMorph(item.text)
                elif morphemetype == PROCLITIC:
                    morph_info[MORPH_IDX] = cleanMorph(item.text) + CLITIC
                else:
                    morph_info[MORPH_IDX] = cleanMorph(item.text)
            # TIER: canonical morpheme (cf)
            elif(item.get('type') == CAN_MORPHEME):
                # TODO: do not assume only 1 circumfix per word
                if morphemetype == CIRCUMFIX: 
                    # if first half of circumfix is word-initial, treat as prefix
                    if numaffix == 1:
                        morph_info[MORPHEME_IDX] = cleanMorph(item.text) + CIRCUM_PRE
                    # if first half of circumfix is not word-initial, treat as infix
                    else:
                        morph_info[MORPHEME_IDX] = CIRCUM_POST + cleanMorph(item.text) + CIRCUM_PRE
                # treat halves circumfix as pre/suffix, treat circumfixed stem as stem
                elif '-...-' in item.text:
                    if morphemetype in STEMS or morphemetype == MWE:
                        morph_info[MORPHEME_IDX] = cleanMorph(item.text).replace('-...-', '')
                    elif morphemetype == PREFIX:
                        morph_info[MORPHEME_IDX] = cleanMorph(item.text).replace('-...-', CIRCUM_PRE)
                    elif morphemetype == SUFFIX:
                        morph_info[MORPHEME_IDX] = CIRCUM_POST + cleanMorph(item.text).replace('-...-', '')
                # other canonical morpheme types
                else:
                    if morphemetype in ENCLITICS:
                        morph_info[MORPHEME_IDX] = CLITIC + cleanMorph(item.text)
                    elif morphemetype == PROCLITIC:
                        morph_info[MORPHEME_IDX] = cleanMorph(item.text) + CLITIC
                    else:
                        morph_info[MORPHEME_IDX] = cleanMorph(item.text)
            # TIER: gloss
            elif (item.get('type') == GLOSS):
                morph_info[GLOSS_IDX] = cleanGloss(item.text, morphemetype)
            # TIER: morpheme pos
            elif(item.get('type') == M_POS):
                morph_info[M_POS_IDX] = cleanPOS(item.text)
                
    return morph_info


# In[18]:


def extract_flextext(flextext_filename):
    '''Takes FLExText XML any number of texts. 
    Extracts words. OUTPUT: 
    [[text_title, 
      text_comment, 
      [*words*
        [*word*
        [line#, word, wPOS, morph, morpheme, gloss, mpos, morphemetype]*morpheme*
        ]]]]'''
    
    #TODO: change output format to JSON/dictionary
    
    
    root = ET.parse(flextext_filename).getroot()
    texts = []
    total_lexemes = 0 # NOTE: MWE is 1 lexeme
    
    for text in root.iter('interlinear-text'):
        title,comment = getTitleComment(text)
        temp_text = [title, comment]
        temp_words = []
        
        # ignoring paragraph breaks
        for phrase in text.iter('phrase'):    
            # FLEx "segnum" is ID for phrase/line/sentence
            segnum = TEMP
            if phrase.find('item').get('type') == 'segnum':
                segnum = phrase.find('item').text
            else:
                segnum = 'NoLine#'

            # "words" or MWE as tokenized by FLEx user or whitespace
            for word in phrase.iter('word'):
                wordtype = word.find('item').get('type')
                wordstring = cleanWord(word.find('item').text)
                
                # ignore punctuation & digits
                if (wordtype != PUNCT and not wordstring.isdigit()):
                    temp_word = []
                    affix_order = [] # to align infixes 
                    total_lexemes+=1
        
                    # get word POS
                    temp_wpos = TEMP # word-level POS
                    for word_item in word.iter('item'):
                        if word_item.get('type') == WORD_POS:
                            temp_wpos = cleanPOS(word_item.text)

                    # get interlinear for word segments, if any
                    if word.find('morphemes') != None:
                        for morph in word.iter('morph'):
                            temp_segment = [segnum, wordstring, temp_wpos]
                            morphemetype = morph.get('type')
                            
                            # TODO: for non-neural models (need input/output alignment)
                            # morpheme type will determine what part of string is infix
                            #affix_order.append(morphemetype)
                            # handle infixes
                            #if len(affix_order) >= 2 and affix_order[-2] in infixes:
                                # NOTE: FLEx seems to always put infix before its stem
                                #preinfix, postinfix = getInfixedStem(str(wrd), morph, temp_word[-1])
                                # insert first half of prefix for surface segmentation
                                #infix_index = len(affix_order)-2
                                #temp_word.insert(infix_index-1, preinfix)
                                # add second half of infixed stem
                                #temp_morph = postinfix
                            #else:
                            
                            temp_morph = getMorpheme(morph, morphemetype)
                            
                            # Add generic gloss to unglossed proper nouns
                            # check gloss index
                            if temp_wpos == 'nprop' and morphemetype in STEMS:
                                if temp_morph[2] == TEMP: 
                                    temp_morph[2] = 'proper_name'
                            
                            # add morpheme to list of word's segments
                            temp_segment.extend(temp_morph)
                            temp_segment.append(morphemetype)
                            
                            temp_word.append(temp_segment)
                            
                    else:
                        temp_word = [[segnum, wordstring, temp_wpos, TEMP, TEMP, TEMP, TEMP, TEMP]]
                        
                    temp_words.append(temp_word)
            
            # TODO: get free translations
            # TODO: handle as many languages if needed
            #en_translation = TEMP
            #id_translation = TEMP
            #temp_phrase_gloss = [p_item for p_item in phrase.iter('item')]
            # make sure the last item is indeed our phrase translation
            #for tpg in temp_phrase_gloss:
            #    if tpg.get('type') == gloss and tpg.get('lang') == ENGLISH:
            #        en_translation = tpg.text
            #    if tpg.get('type') == gloss and tpg.get('lang') == INDONESIAN:
            #        id_translation = tpg.text
            #append metadata the translation of the phrase to the end of the temp line
            #temp_line.append(en_translation)
            #temp_line.append(id_translation)
            
        # add words to text
        temp_text.append(temp_words)
        texts.append(temp_text)
    
    # corpus statistics
    print("Total tokenized lexemes, ignoring punctuation and digits:", total_lexemes, end='\n\n')
    # sanity check first 10 words
    print(texts[0][2][:18], end='\n\n')
    
    return texts


# ### Filtering 

# In[19]:


def glossed(wordlistofmorphemes):
    '''checks for glosses, 
        assumes segmentation is complete'''
    
    glossed = True
    for segment in wordlistofmorphemes:
        if segment[5] == TEMP:
            glossed = False
            break # this line saves time 
    return glossed
    
    
def annotated(wordlistofmorphemes):
    '''skipping words that have not been annotated 
    (i.e. no <morphemes> tag in XML)'''
    
    annotated = True
    if len(wordlistofmorphemes) == 1:
        if wordlistofmorphemes[0][3] == TEMP:
            annotated = False
    return annotated


def multiword(wordlistofmorphemes):
    
    mwe = False
    if ' ' in wordlistofmorphemes[0][1]:
        mwe = True
    return mwe


def quality_check(extractedtexts):
    '''Write custom filter functions above, add calls here
        Un/comment lines with filter calls as needed'''
    
    good = []
    bad = []
    good_cnt = 0
    
    for text in extractedtexts:
        for word in text[-1]:
            if glossed(word) and annotated(word) and not multiword(word):
                good.append(word)
                good_cnt+=1
            else:
                bad.append(word)
    
    print("Total segmented and glossed lexemes:", good_cnt, end='\n\n')
    return good,bad


# # Write to files

# In[20]:


def check_alignment(a, b):
    if len(a) != len(b):
        raise ValueError("morph(emes) and gloss must be same amount in a word")
        

def extract2file(extracted_data, purpose, outfilepath):
    '''Writes two files: x and Y (data and annotations; input and output)
    No text or line divisions, just list of tokens
    Purpose variable determines what will be preserved in file,
    possibilities match output types variables
    gls = glossing only, seggls = segmentation+glossing, pos = (word) POS tagging'''
    
    input_data = []
    output_data = []
    
    for word in extracted_data: 
        input_data.append(' '.join(word[0][1])) # text token with space delimiter
            
        # output types
        wPOS_tag = word[0][2]
        canonical_morphemes = []
        surface_morphemes = []
        morpheme_glosses = []
        for morpheme in word:
            canonical_morphemes.append(morpheme[3])
            surface_morphemes.append(morpheme[4])
            morpheme_glosses.append(morpheme[5])

        # final output data
        if purpose == '_pos':
            output_data.append(wPOS_tag)
        elif purpose == '_can_seg':
            output_data.append(' '.join(canonical_morphemes))
        elif purpose == '_surf_seg':
            output_data.append(' '.join(surface_morphemes))
        #TODO: purpose == 'can_seg_gls' ...allow for null morphemes
        elif purpose == '_surf_seg_gls':
            check_alignment(surface_morphemes, morpheme_glosses)
            combined_seg_gls = []
            for i, morpheme in enumerate(surface_morphemes):
                combined_seg_gls.append(morpheme+'#'+morpheme_glosses[i])
            output_data.append(' '.join(combined_seg_gls))

    with open(outfilepath+purpose+'.input', 'w', encoding='utf8') as I, open(outfilepath+purpose+'.output', 'w', encoding='utf8') as O:
        I.write('\n'.join(input_data))
        O.write('\n'.join(output_data))


# # Sample Run Code: Extract Surface Segmentation Data to Files

# In[21]:


datalocation = r"../../../OneDrive - University of Florida/AL/data/"
flexdata = [r'./FLExtexts/lez-all_txts_2019.flextext', r'./FLExtexts/lez-all_txts_2022.flextext']

for dbfile in flexdata:
    name = os.path.basename(dbfile).split('.')[0]
    print('\n', name)
    master_data = extract_flextext(dbfile)

    # filter for my training purposes, split data lacking necessary annotations
    # returns list of words
    trainable_words, unannotated_words = quality_check(master_data)
    print(trainable_words[:18])

    # write all extracted words to _M(aster) file 
    # write unannotated data (for my purposes) to _U(nlabeled) file
    # write annotated data to separate file

    #extract2file(master_data, '_seg', datalocation+name+'_M')
    extract2file(unannotated_words, '_surf_seg', datalocation+name+'_U')
    extract2file(trainable_words, '_surf_seg', datalocation+name)


# In[ ]:




