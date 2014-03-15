# -*- coding: utf-8 -*-

import re
import os
import sys
import xbmc
import urllib
import xbmcvfs
import xbmcaddon
import xbmcgui,xbmcplugin
from bs4 import BeautifulSoup

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")

sys.path.append (__resource__)

YYETS_API = 'http://www.yyets.com/search/index?keyword=%s&type=subtitle'

def log(module, msg):
    xbmc.log((u"%s::%s - %s" % (__scriptname__,module,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )

def normalizeString(str):
    return str

def Search( item ):
    subtitles_list = []

    log( __name__ ,"Search for [%s] by name" % (os.path.basename( item['file_original_path'] ),))
    if item['mansearch']:
        url = YYETS_API % (item['mansearchstr'])
    else:
        url = YYETS_API % (item['title'])
    socket = urllib.urlopen( url )
    data = socket.read()
    socket.close()
    soup = BeautifulSoup(data)
    results = soup.find_all("li", attrs={"class":"clearfix"})
    for it in results:
        if it.div.text == '字幕'.decode('utf-8'):
            link = it.a.get('href').encode('utf-8')
            version = it.find(text='版本:'.decode('utf-8')).next.encode('utf-8')
            if version == '<br/>': version = '未知版本'
            match = re.search('\[(.*?)\]', it.a.strong.next_sibling)
            if match:
                langs = match.group(1).encode('utf-8').split('/')
                for lang in langs:
                    name = '%s (%s)' % (version, lang)
                    if 'chi' in item['3let_language'] and lang in ('简体', '繁体', '中英'):
                        subtitles_list.append({"language_name":"Chinese", "filename":name, "link":link, "language_flag":'zh', "rating":"0", "lang":lang})
                    if 'eng' in item['3let_language'] and lang == '英文':
                        subtitles_list.append({"language_name":"English", "filename":name, "link":link, "language_flag":'en', "rating":"0", "lang":lang})

    if subtitles_list:
        for it in subtitles_list:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                  label2=it["filename"],
                                  iconImage=it["rating"],
                                  thumbnailImage=it["language_flag"]
                                  )

            listitem.setProperty( "sync", "false" )
            listitem.setProperty( "hearing_imp", "false" )

            url = "plugin://%s/?action=download&link=%s&lang=%s" % (__scriptid__,
                                                                        it["link"],
                                                                        it["lang"]
                                                                        )
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

def rmtree(path):
    if isinstance(path, unicode):
        path = path.encode('utf-8')
    dirs, files = xbmcvfs.listdir(path)
    for dir in dirs:
        rmtree(os.path.join(path, dir))
    for file in files:
        xbmcvfs.delete(os.path.join(path, file))
    xbmcvfs.rmdir(path)

def Download(url,lang):
    if xbmcvfs.exists(__temp__):
        rmtree(__temp__)
    xbmcvfs.mkdirs(__temp__)

    subtitle_list = []
    exts = [".srt", ".sub", ".txt", ".smi", ".ssa", ".ass" ]
    fulllist = ['简体', 'chs', '繁体', 'cht', '英文', 'eng', '简体&英文', '繁体&英文']
    dict = {'简体':['简体', 'chs'],
            '繁体':['繁体', 'cht'],
            '英文':['英文', 'eng'],
            '简英':['简体&英文'],
            '繁英':['繁体&英文']}
    if lang == '中英':
        if xbmc.getLanguage() == 'Chinese (Traditional)':
            langlist = dict['繁英']
        else:
            langlist = dict['简英']
    else:
        langlist = dict[lang]

    socket = urllib.urlopen( url )
    data = socket.read()
    soup = BeautifulSoup(data)
    url = soup.find("div", attrs={"class":"zm_downlinks"}).a.get('href').encode('utf-8')
    socket = urllib.urlopen( url )
    url = socket.geturl()            # get redirection url
    zipext = os.path.splitext(url)[1]
    zip = os.path.join( __temp__, "YYETS"+zipext)
    with open(zip, "wb") as subFile:
        subFile.write(socket.read())
    subFile.close()
    socket.close()
    xbmc.sleep(500)
    xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip,__temp__,)).encode('utf-8'), True)
    path = __temp__
    dirs, files = xbmcvfs.listdir(path)
    if len(dirs) > 0:
        path = os.path.join(__temp__, dirs[0].decode('utf-8'))
        dirs, files = xbmcvfs.listdir(path)
    if len(files) == 1:
        subtitle_list.append(os.path.join(path, files[0].decode('utf-8')))
    else:
        for subfile in files:
            if (os.path.splitext( subfile )[1] in exts) and (subfile.split('.')[-2] in langlist):
                subtitle_list.append(os.path.join(path, subfile.decode('utf-8')))
        if not subtitle_list:
            for subfile in files:
                if (os.path.splitext( subfile )[1] in exts) and not(subfile.split('.')[-2] in fulllist):
                    subtitle_list.append(os.path.join(path, subfile.decode('utf-8')))

    return subtitle_list

def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=paramstring
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]

    return param

params = get_params()
if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp']               = False
    item['rar']                = False
    item['mansearch']          = False
    item['year']               = xbmc.getInfoLabel("VideoPlayer.Year")                           # Year
    item['season']             = str(xbmc.getInfoLabel("VideoPlayer.Season"))                    # Season
    item['episode']            = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                   # Episode
    item['tvshow']             = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))   # Show
    item['title']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")) # try to get original title
    item['file_original_path'] = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))  # Full path of a playing file
    item['3let_language']      = []

    if 'searchstring' in params:
        item['mansearch'] = True
        item['mansearchstr'] = params['searchstring']

    for lang in urllib.unquote(params['languages']).decode('utf-8').split(","):
        item['3let_language'].append(xbmc.convertLanguage(lang,xbmc.ISO_639_2))

    if item['title'] == "":
        item['title']  = xbmc.getInfoLabel("VideoPlayer.Title")                       # no original title, get just Title
        if item['title'] == os.path.basename(xbmc.Player().getPlayingFile()):         # get movie title and year if is filename
            title, year = xbmc.getCleanMovieTitle(item['title'])
            item['title'] = normalizeString(title.replace('[','').replace(']',''))
            item['year'] = year

    if item['episode'].lower().find("s") > -1:                                        # Check if season is "Special"
        item['season'] = "0"                                                          #
        item['episode'] = item['episode'][-1:]

    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']  = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]

    Search(item)

elif params['action'] == 'download':
    subs = Download(params["link"], params["lang"])
    for sub in subs:
        listitem = xbmcgui.ListItem(label=sub)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
