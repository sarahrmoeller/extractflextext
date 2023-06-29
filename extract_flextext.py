#!/usr/bin/env python
# coding: utf-8

# In[36]:


import xml.etree.ElementTree as ET # parses XML files
import string
import os


# # Extract Data from flextext XML files

# In[37]:


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


# In[38]:


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


# In[39]:


#############################
'''These cleaning functions handle pecularities of a corpus or non-conventional IGT annotations'''
#TODO: reverse before reimporting to FLEx

def cleanWord(IGTstring):  
    
    IGTstring = str(IGTstring)
    
    # TODO?: phrasal lexemes separated by double tilde
    #IGTstring = IGTstring.strip().replace(' ', '~~')
    # remove hyphen when it is a Cyrillic quotation mark 
    IGTstring = IGTstring.strip('-')
    # tilde in hyphenated words to reduce confusion with morpheme breaks
    IGTstring = IGTstring.replace('-', '~')
    
    return IGTstring.strip().lower()
    
    
def cleanMorph(IGTstring):
    '''remove unexpected symbols in surface morphs and canonical morphemes
    (includes infixes and circumfix halves)'''
    
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
    
    ### NOTE: add here any pre-processing specific to a database
    IGTstring = IGTstring.replace('N (kx cl)', 'N(kx.cl)') ## Natugu [ntu] morpheme pos
    
    return IGTstring.strip()   


# In[40]:


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


# In[41]:


def getMorpheme(morphitem, morphemetype, numaffix):
    '''OUTPUT for each morpheme segment: [morph, morpheme, gloss, mpos]
    To add more items to this array of info about morpheme segments:
    1st. Add another holding place in the morph_info array; give index for that info piece.
    2nd. Add elif statement for new tier using the attribute you want, e.g. 'morpheme type'.
        If necessary, create special delimiter and write "cleaning" function.
    3rd. Check that that morph_info array matches entries in temp_morph
        and does not mess up punctuation processing.'''
    
    # temporary array for morpheme information
    morph_info = [TEMP, TEMP, TEMP, TEMP, morphemetype]
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
                    if len(numaffix) == 1:
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


# ## Main Extraction Function

# In[42]:


def extract_flextext(flextext_filename):
    '''Takes FLExText XML any number of texts. OUTPUT list of line dicts: 
    [{"text_title":title, "text_comment":comment, "lineid":line#, "line_txt":words_digits_string, words":[
            {"orig_word":word, "POS":postag, "morphemes":[
                [morph, morpheme, gloss, mpos, morphemetype]
    ]}]}]'''
    
    #TODO: add "orig_line":line

    root = ET.parse(flextext_filename).getroot()
    lines = []
    total_lexemes = 0 # NOTE: MWE is 1 lexeme
    pos_tags_in_corpus = set()
    
    for text in root.iter('interlinear-text'):
        title,comment = getTitleComment(text)
        
        # ignoring paragraph breaks
        for line_i,phrase in enumerate(text.iter('phrase')):
            temp_line = {}
            temp_words = []
            no_punct_line = ''
            # FLEx "segnum" is ID for phrase/line/sentence
            segnum = TEMP
            if phrase.find('item').get('type') == 'segnum':
                segnum = phrase.find('item').text
            else:
                segnum = str(line_i)

            # "words" or MWE as tokenized by FLEx user
            for word in phrase.iter('word'):
                wordtype = word.find('item').get('type')
                wordstring = cleanWord(word.find('item').text)
                # ignore punctuation & digits
                #if wordtype != PUNCT and not wordstring.isdigit() and wordstring != '~' and wordstring != '':
                # ignore punctuation only
                if wordtype != PUNCT and wordstring != '~' and wordstring != '':
                    temp_morphemes = []
                    affix_order = [] # to align infixes 
                    no_punct_line += wordstring
                    total_lexemes+=1
                    
                    # get word POS
                    temp_wpos = TEMP # word-level POS
                    for word_item in word.iter('item'):
                        if word_item.get('type') == WORD_POS:
                            temp_wpos = cleanPOS(word_item.text)
                    # generic POS for digits
                    if wordstring.isdigit():
                        temp_wpos = 'num'
                    pos_tags_in_corpus.add(temp_wpos)
                    
                    # get interlinear for word segments, if any
                    if word.find('morphemes') == None:  #TODO?: eliminate this line, use filter function
                        temp_morphemes.append([TEMP, TEMP, TEMP, TEMP, TEMP])
                    else:
                        for morph in word.iter('morph'):
                            morphemetype = morph.get('type')
                            
                            # TODO: for non-neural models (need input/output alignment)
                            # morpheme type will determine what part of string is infix
                            affix_order.append(morphemetype)
                            
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
                            
                            temp_morph = getMorpheme(morph, morphemetype, affix_order)
                            
                            # Add generic gloss to unglossed proper nouns
                            # check gloss index
                            if temp_wpos == 'nprop' and morphemetype in STEMS:
                                if temp_morph[2] == TEMP: 
                                    temp_morph[2] = 'proper_name'
                            
                            # add morpheme to dict of word's segments
                            temp_morphemes.append(temp_morph)
                    
                    # create word dict
                    temp_words.append({"orig_word":wordstring,"POS":temp_wpos,"morphemes":temp_morphemes})
            
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
            
        
            # add line
            temp_line = {"text_title":title, "text_comment":comment, "lineid":segnum, "line_txt":no_punct_line, "words":temp_words}
            lines.append(temp_line)
    
    # corpus statistics
    print("Part of speech found:", pos_tags_in_corpus, end='\n\n')
    print("Tokenized lexemes, ignoring punctuation and digits:", total_lexemes, end='\n\n')
    # sanity check first line
    print(lines[0]["words"][:10])
    print()
                                
    return lines


# ### Filtering 
# 
# word_by_morpheme -> `lines["words"][word_idx]["morphemes"]`, i.e. [[morph, morpheme, gloss, mpos, morphemetype],...]
# 
# lexical_item -> `lines[words][word_idx]["orig_word"]`, i.e. wordstring
# 
# #### Morpheme level Filters

# In[43]:


def glossed(word_by_morphemes):
    '''no words with missing glosses;
        assumes segmentation is complete'''
    
    glossed = True
    for segment in word_by_morphemes:
        # check gloss of morphemes
        if segment[2] == TEMP:
            glossed = False
            break # this line saves time 
    return glossed
    
    
def surf_segmented(word_by_morphemes):
    '''no words that have not been segmented 
    (i.e. no <morphemes> tag in XML)'''
    
    annotated = True
    if len(word_by_morphemes) == 1:
        # check surface morpheme
        if word_by_morphemes[0][0] == TEMP:
            annotated = False
        #TODO: check canonical morpheme
    return annotated


# #### Word level filters

# In[44]:


def multiword(lexical_item):
    '''no lexical items with spaces'''
    
    mwe = False
    # check original text of word
    if ' ' in lexical_item or '~' in lexical_item or '-' in lexical_item:
        mwe = True
    return mwe


def selected_pos(word_postag):
    '''filter for a list of specified word level POS'''
    
    undesired_pos = False
    # check word level POS tag
    if word_postag not in SELECT_POS_TAGS:
            undesired_pos = True
    return undesired_pos


# #### COMBINE FILTER FUNCTIONS HERE 

# In[45]:


def quality_check(extractedtexts):
    '''Write custom filter functions above, add calls here
        add/remove function calls as needed. 
        Returns list of words as list of morphemes'''
    
    good = []
    bad = []
    good_cnt = 0
    for line in extractedtexts:
        for word in line["words"]:
            ### add word level function  to completely eliminate a filtered word/POS
            # uncomment line below if filtering for specific POS tags
            #if not multiword(word['orig_word']) and selected_pos(word['POS']) and word['POS'] == 'num':
            if not multiword(word['orig_word']) and not word['POS'] == 'num':
                ### add morpheme level filtering functions below, use only one line ###
                # uncomment line below if purpose is gls or seggls (not seg only)
                #if glossed(word["morphemes"]) and surf_segmented(word["morphemes"]):
                # uncomment line below if surface seg only (not gls)
                #if surf_segmented(word["morphemes"]):
                # uncomment line below if using all three
                if glossed(word["morphemes"]) and surf_segmented(word["morphemes"]) and surf_segmented(word["morphemes"]):
                    good.append(word)
                    good_cnt+=1
                # filtered words go to unlabeled dataset    
                else:
                    bad.append(word)

    print("Total after filtering:", good_cnt, end='\n\n')
    return good,bad


# # Write to files
# 
# Get this list of words:  
# 
# Current: `[{"text_title":title, "text_comment":comment, "lineid":line#, "words":[
#             {"orig_word":word, "POS":postag, "morphemes":[
#                 [morph, morpheme, gloss, mpos, morphemetype]
#     ]}]}]` 
# 
# Old: `[{"text_title":title, "text_comment":comment, "words":[
#             {"segnum":line#, "orig_word":word, "POS":postag, "morphemes": [
#                             [morph, morpheme, gloss, mpos, morphemetype]
#                          ]}]` 
# 
# to files with one word per line

# In[46]:


def check_alignment(a, b):
    if len(a) != len(b):
        raise ValueError("morph(emes) and gloss must be same amount in a word")
        

def dataFiles(extracted_words, purpose, outfilepath):
    '''Writes two files: x and Y (data and annotations; input and output)
    No text or line divisions.
    Possible purposes: gls = glossing only, seg_gls = segmentation+glossing, pos = (word) POS tagging'''
    
    input_data = []
    output_data = []
    
    for word in extracted_words: 
        # input string (x)
        input_data.append(' '.join(word["orig_word"])) # space between letters
            
        # output types (Y)
        wPOS_tag = word["POS"]
        canonical_morphemes = []
        surface_morphemes = []
        morpheme_glosses = []
        for morpheme in word["morphemes"]:
            surface_morphemes.append(morpheme[0])
            canonical_morphemes.append(morpheme[1])
            morpheme_glosses.append(morpheme[2])

        # determines what will be written to output file
        #TODO: purpose == _canSegGls & _canSeg must handle null morphemes
        if purpose == '_pos':
            output_data.append(wPOS_tag)
        elif purpose == '_gls':
            output_data.append(' '.join(morpheme_glosses))
        elif purpose == '_canSeg':
            output_data.append(' '.join(canonical_morphemes))
        elif purpose == '_surSeg':
            output_data.append(' '.join(surface_morphemes))
        elif purpose == '_surSegGls':
            check_alignment(surface_morphemes, morpheme_glosses)
            combined_seg_gls = []
            for i, morpheme in enumerate(surface_morphemes):
                combined_seg_gls.append(morpheme+'#'+morpheme_glosses[i])
            output_data.append(' '.join(combined_seg_gls))
        else:
            print("Output format not found.")

    with open(outfilepath+purpose+'.input', 'w', encoding='utf8') as I, open(outfilepath+purpose+'.output', 'w', encoding='utf8') as O:
        I.write('\n'.join(input_data))
        O.write('\n'.join(output_data))


# # Sample Run Code: Extract Surface Segmentation Data to Files

# In[55]:


####### EXTRACT #######
def main(dbfile, tasks):
    ####### FOR FILTERING ####### 
    # lezgi pos tags: {'ordnum', 'Vnf', 'num', 'indfpro', 'nprop', 'emph', 'Vocpart', 'proform', 'multipnum', 'prep', 'adv', 'post', 'ptcp', 'pers', 'verbprt', 'coordconn', 'adj', 'v', 'conn', 'poss', 'pro', 'prt', 'det', 'dem', 'interj', 'msd', 'subordconn', 'Vf', 'cardnum', 'n', 'interrog', 'recp'}
    # Alas pos tags: {'num', 'n', 'refl', 'Aux', 'vt', 'cop', 'clf', 'adv', 'prt', 'Adj', 'cardnum', 'vi', 'stc', 'existmrkr', 'quant', 'relpro', 'ordnum', 'vd', 'distrnum', 'adj', 'Prep', 'nprop', 'interj', 'Conj', 'dem', 'v', 'pro'}
    #SELECT_POS_TAGS = ['Vnf', 'v', 'msd', 'Vf','n','IMPV','cop']
    file_ext = ''

    ####### FILE LOCATIONS ####### 
    LANG = 'ntu'
    datalocation = r"../../../OneDrive - University of Florida/AL/data/"+LANG+'/'
    to_extract = [r'./flextexts/'+LANG+'-all_txts.flextext']
    #TASKS = ['_canSeg', '_surSeg', '_gls', '_canSegGls', '_surSegGls', '_pos']

    datalines = extract_flextext(dbfile)

    # filter for my training purposes, split data lacking necessary annotations
    # returns list of words
    trainable_words, unannotated_words = quality_check(datalines)
    print(trainable_words[:10])
    print(unannotated_words[:10])
    
    for task in tasks:
        # write all extracted words to _M(aster) file 
        #extract2file(master_data, '_seg', datalocation+name+'_M')
        # write unannotated data (for my purposes) to _U(nlabeled) file
        dataFiles(unannotated_words, task, datalocation+LANG+'_U'+file_ext)
        # write annotated data to separate file
        dataFiles(trainable_words, task, datalocation+LANG+'_L'+file_ext)


# In[56]:


main(to_extract[0], ['_surSeg', '_gls', '_surSegGls', '_pos'])


# In[ ]:




