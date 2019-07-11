#!/usr/bin/python 
# -*- encoding: utf-8 -*-

"""
This script allows to recreate all the shares of a user during a server-to-server migration 

Use : 

python get_share_info.py user@domain 

the result is stored in 

/tmp/user@domain.zmprov 



"""


import csv,urllib2,os,commands,base64,sys,re,time
from xml.dom.minidom import parse, parseString, Document
import xml.etree 
from xml.etree import ElementTree
import codecs

migrateuser=sys.argv[1]
downloadfile='/tmp/contact.csv'
file_to='/tmp/newcontact.csv'
sharefile='/tmp/recreateshare.zmprov'
ZIMBRA_SOAP_SERVICE = "https://127.0.0.1:7071/service/admin/soap/"
ZIMBRA_ADMIN_SOAP_SERVICE = "https://127.0.0.1:7071/service/admin/soap/"

#ADMINISTRATOR ACCOUNT 
ZIMBRA_ADMIN_USERNAME = ""

#PASSWORD 
ZIMBRA_ADMIN_PASSWORD = ""

ZIMBRA_SOAP_HEADERS = {
    'Content-type': 'text/xml; charset=utf-8',
}


ZIMBRA_AUTH_REQUEST = '''<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"> 
        <soap:Body>
            <AuthRequest xmlns="urn:zimbraAdmin">
                <name>%s</name>
                <password>%s</password>
            </AuthRequest>
        </soap:Body>
    </soap:Envelope>'''

ZIMBRA_REQUEST = '''<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
        <soap:Header>
            <context xmlns="urn:zimbra">
                <userAgent xmlns="" name="StarXpert SOAP Provisionning" version="0.0.1"/>
                <authToken>%s</authToken>
                <sessionId id="%s" type="admin">%s</sessionId>
                <account by="name">%s</account>
            </context>
        </soap:Header>
        <soap:Body>%s</soap:Body>
    </soap:Envelope>'''

ZIMBRA_REQUEST_SHARE = '''<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
        <soap:Header>
            <context xmlns="urn:zimbra">
                <userAgent xmlns="" name="StarXpert SOAP Provisionning" version="0.0.1"/>
                <authToken>%s</authToken>
                <nosession/>
            </context>
        </soap:Header>
        <soap:Body>%s</soap:Body>
    </soap:Envelope>'''




ZIMBRA_GET_REQUEST = '''<GetAccountRequest xmlns="urn:zimbraAdmin">
        <account by="name">%s</account>
    </GetAccountRequest>'''


ZIMBRA_GET_FOLDER_REQUEST = '''<GetFolderRequest xmlns="urn:zimbraMail" visible="1" needGranteeName="1"></GetFolderRequest>'''
ZIMBRA_GET_FOLDER_REQUEST = '''<GetFolderRequest xmlns="urn:zimbraMail" ></GetFolderRequest>'''


ZIMBRA_GET_SHARE_INFO= '''   <GetShareInfoRequest xmlns="urn:zimbraAdmin">
      <owner by="name">%s</owner>
      </GetShareInfoRequest>
'''


class UTF8Recoder:
    '''
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    '''
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    '''
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    '''

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    '''
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    '''

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class ZimbraIntegration:
    def __init__(self):
        self.__authToken = None
        self.__sessionId = None
        self.__url       = ZIMBRA_ADMIN_SOAP_SERVICE
        self.__urluser   = ZIMBRA_SOAP_SERVICE
        self.__username  = ZIMBRA_ADMIN_USERNAME
        self.__password  = ZIMBRA_ADMIN_PASSWORD

    def __envelope(self, request, name):
        if self.__authToken is None:
            self.__getAuthToken()

        envelope = ZIMBRA_REQUEST_SHARE % (self.__authToken,  request)
        return envelope

    def __sendRequest(self, request):
        req = urllib2.Request(self.__urluser, request, ZIMBRA_SOAP_HEADERS)
        try:
            resp = urllib2.urlopen(req)
            tree = parse(resp)
        except urllib2.HTTPError, e:
            print e
            tree = ElementTree.parse(e.fp)
            error = tree.findtext(
                "//{http://www.w3.org/2003/05/soap-envelope}Text")
            raise ZimbraIntegrationException(error)
        return tree

    def __sendRequestAdmin(self, request):
        req = urllib2.Request(self.__url, request, ZIMBRA_SOAP_HEADERS)
        try:
            resp = urllib2.urlopen(req)
            tree = ElementTree.parse(resp)
        except urllib2.HTTPError, e:
            print e
            tree = ElementTree.parse(e.fp)
            error = tree.findtext(
                "//{http://www.w3.org/2003/05/soap-envelope}Text")
            raise ZimbraIntegrationException(error)
        return tree

    def __getAuthToken(self):
        requestBody = ZIMBRA_AUTH_REQUEST % (self.__username, self.__password)
        tree = self.__sendRequestAdmin(requestBody)
        self.__authToken = tree.findtext(".//{urn:zimbraAdmin}authToken")
        self.__sessionId = tree.findtext(".//{urn:zimbraAdmin}sessionId")


    def getFolders(self, name):
        requestBody = ZIMBRA_GET_FOLDER_REQUEST
        requestBody = self.__envelope(requestBody, name)
        tree = self.__sendRequest(requestBody)
        return tree

    def getShare(self, name,file):
	requestBody = ZIMBRA_GET_SHARE_INFO % (migrateuser)
	requestBody = self.__envelope(requestBody, name)
	try:
		tree = self.__sendRequest(requestBody)
		file.write(tree.toxml())
		return file
	except xml.parsers.expat.ExpatError, ex:
		print 'ERROR with'+migrateuser 
		return self.getShare(migrateuser,file)

class ZimbraIntegrationException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason


def GetFile(url1):
	proxy_handler = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_handler)
	request= urllib2.Request(url1)
	base64string = base64.encodestring('%s:%s' % (ZIMBRA_ADMIN_USERNAME, ZIMBRA_ADMIN_PASSWORD)).replace('\n', '')
	request.add_header("Authorization", "Basic %s" % base64string)   
        urllib2.install_opener(opener)
        f = urllib2.urlopen(request)
        code = f.read()
        with open(downloadfile, "wb") as csv_file:
        	csv_file.write(code)
        f.close()



def parseXML(xml):
	tree=ElementTree.fromstring(xml)
        root= tree.find('.//{http://www.w3.org/2003/05/soap-envelope}Body/{urn:zimbraAdmin}GetShareInfoResponse')
	sharefile="/tmp/"+migrateuser+".zmprov"
	f=codecs.open(sharefile,'w',encoding='utf8')
	
	for i in root:
		share=i.attrib
		if share['granteeName'] == '':
			continue
		if 'usr' in share['granteeType']:
			share['folderPath']=share['folderPath'].replace("'",'_')
			f.write("sm "+share['ownerEmail']+" mfg  '"+share['folderPath']+"'    account "+share['granteeName']+" "+share['rights']+"\n" )
			f.write("sm "+share['granteeName']+" cm --view "+share['view']+" '"+share['folderPath']+" "+share['ownerEmail']+"'  "+share['ownerEmail']+"   '"+share['folderPath']+"'\n")
		else:
                        f.write("sm "+share['ownerEmail']+" mfg  '"+share['folderPath']+"'    group  "+share['granteeName']+" "+share['rights']+"\n" )

xmlfile="/tmp/tmp.xml"
file=codecs.open(xmlfile,'w',encoding='utf8')
zi = ZimbraIntegration()
t= zi.getShare(migrateuser,file)
if t is False: 
	print 'ERROR with'+migrateuser
	exit()
t.close()

f=open("/tmp/tmp.xml",'r')
share=parseXML(f.read())


