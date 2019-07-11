#!/usr/bin/python
# -*- coding: utf8 -*-

"""
This script convert the data in the roudcube and horde database to VCS and ICS FILE 

to execute : 

    python extractvcfroundcube.py login loginhorde loginroudcube

"""
import MySQLdb,os,sys,shutil

login= sys.argv[1]
pnom=sys.argv[2].lower()
user=sys.argv[3]
path = '/tmp/'+user+"/vcf"
pathics = '/tmp/'+user+"/ics"
try:
        os.makedirs(path)
	os.makedirs(pathics)
except:
        shutil.rmtree(path)
	shutil.rmtree(pathics)
        os.makedirs(path)
	os.makedirs(pathics)

def dbconnectroudcube():
        db = MySQLdb.connect(host="HOSTDB",
                             user="ROUNDCUBEUSER", # your username
                             passwd="PASSWORD", # your password
                             db="ROUNDCUBEDB")
        cur = db.cursor()
        return cur

def dbconnecthorde():
        db = MySQLdb.connect(host="HOSTDB",
                             user="HORDEUSER", # your username
                             passwd="PASSWORD", # your password
                             db="HORDEDB")
        horde = db.cursor()
        return horde


def requete(pnom,login,cur):
	hordenum=[]
        cur.execute("SELECT name, email,firstname, surname,vcard  FROM contacts LEFT JOIN users ON users.user_id = contacts.user_id WHERE users.username='"+pnom+"';".encode('UTF-8'))
	roudcube = cur.fetchall()
	if not roudcube:
		cur.execute("SELECT name, email,firstname, surname,vcard  FROM contacts LEFT JOIN users ON users.user_id = contacts.user_id WHERE users.username='"+login+"';".encode('UTF-8'))
		roudcube = cur.fetchall()
		if not roudcube:
			horde.execute("select share_name from turba_sharesng WHERE share_owner LIKE '"+pnom+"@univ-montp2.fr' ;".encode('UTF-8'))
			idhorde=horde.fetchall()
			if not idhorde:
				horde.execute("select share_name from turba_sharesng WHERE share_owner LIKE '"+login+"@univ-montp2.fr';".encode('UTF-8'))
				idhorde=horde.fetchall()
				if not idhorde:
					horde.execute("SELECT object_email,object_workphone,object_cellphone,object_title,object_company,object_firstname,object_lastname FROM turba_objects where owner_id LIKE '"+pnom+"@univ-montp2.fr';".encode('UTF-8'))
					hordenum=horde.fetchall()
					if not hordenum:
						horde.execute("SELECT object_email,object_workphone,object_cellphone,object_title,object_company,object_firstname,object_lastname FROM turba_objects where owner_id LIKE '"+login+"@univ-montp2.fr';".encode('UTF-8'))
						hordenum=horde.fetchall()
						if not hordenum:
							print 'PAS DE CONTACT'
							sys.exit()
				else:
					horde.execute("SELECT object_email,object_workphone,object_cellphone,object_title,object_company,object_firstname,object_lastname FROM turba_objects where owner_id LIKE '"+idhorde[0][0]+"';".encode('UTF-8'))
					hordenum=horde.fetchall()
					if not hordenum:
		                                print 'PAS DE CONTACT'
                		                sys.exit()

			else:
				horde.execute("SELECT object_email,object_workphone,object_cellphone,object_title,object_company,object_firstname,object_lastname FROM turba_objects where owner_id LIKE '"+idhorde[0][0]+"';".encode('UTF-8'))
				hordenum=horde.fetchall()
				if not hordenum:
					print 'PAS DE CONTACT'
					sys.exit()
			
        return roudcube,hordenum

def createvcf(roudcube,hordenum):
        vcf=[]
        for row in roudcube:
                if row[4]:
                        vcf.append(row[4])
                else:
                        create=('BEGIN:VCARD\nVERSION:3.0\nEMAIL:'+row[1]+'\nN:'+row[3]+';'+row[2]+';;;\nFN:'+row[0]+'\nEND:VCARD\n')
                        vcf.append(create)
	for row in hordenum:
		create=('BEGIN:VCARD\nVERSION:3.0\nEMAIL:'+row[0]+'\nN:'+row[6]+';'+row[5]+';;;\nFN:'+row[6]+' '+row[5]+'\nTEL;TYPE=WORK:'+row[1]+'\nTEL;TYPE=CELL:'+row[2]+'\nTITLE:'+row[3]+'\nORG:'+row[4]+'\nEND:VCARD\n')
		vcf.append(create)
        return vcf

cur=dbconnectroudcube()
horde=dbconnecthorde()
roudcube,hordenum = requete(pnom,login,cur)

filevcf=createvcf(roudcube,hordenum)
f = open(path+"/"+user+".vcf","w")
for item in filevcf:
  f.write("%s\n" % item)
f.close()

