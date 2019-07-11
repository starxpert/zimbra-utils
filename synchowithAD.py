#!/usr/bin/python
# -*- encoding: utf-8 -*-

"""

This script allow to synchronise an ActiveDirectory with Zimbra

When an user have an email address in its AD  record e, this one is compared to the ZImbra OpenLdap directory, the synchronization created the accounts, modifies them in the last 15 min or farms if the account is locked or if deleted in the AD 

"""


import ldap,os,getopt,sys,commands,smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

verbose=True
send_mail = False
smtp_sender=""
smtp_recipient=""
smtp_host="localhost"
zmprov_file = "/tmp/synchroAD.zmprov"
ldap_protocol = 'ldaps://'
ldapZIMBRA_protocol = 'ldap://'
ldap_host1 = ''
ldap_host2 = ''
ldap_port = 636
ldap_user = ''
ldap_pass = ''
ldap_base_dn=''


status,output = commands.getstatusoutput("/opt/zimbra/bin/zmlocalconfig ldap_host")
ldap_ZIMBRA1 = output.split(" = ")[1]
status,output = commands.getstatusoutput("/opt/zimbra/bin/zmlocalconfig ldap_port")
ldap_portZIMBRA = output.split(" = ")[1]
status,output = commands.getstatusoutput("/opt/zimbra/bin/zmlocalconfig zimbra_ldap_userdn")
ldap_ZIMBRAuser = output.split(" = ")[1]
status,output = commands.getstatusoutput("/opt/zimbra/bin/zmlocalconfig -s zimbra_ldap_password")
ldap_ZIMBRApass = output.split(" = ")[1]

ldap_ZIMBRAbase_dn=''

ldap_portZIMBRA = 389

heure = datetime.now()

report_mail = []
list_attr = {} #Ne pas supprimer meme si on reprends pas d'attribus
#AD attribue | Zimbra attribue
#Cela par contre on peu
list_attr['givenName']='givenName'
list_attr['sn']='sn'
list_attr['sAMAccountName']='cn'
list_attr['displayName']='displayName'
list_attr['title']='title'
list_attr['telephoneNumber']='telephoneNumber'
list_attr['company']='description'
list_attr['facsimileTelephoneNumber']='facsimileTelephoneNumber'
list_attr['mobile']='mobile'
list_attr['street']='street'
list_attr['l']='l'
list_attr['postalCode']='postalCode'
list_attr['company']='description'
list_attr['userPrincipalName']='zimbraAuthLdapExternalDn'
list_attr['department']='o'


def err_report(in_msg):
        if not send_mail:
                return
        msg = MIMEText(in_msg,'plain','utf-8')
        msg['Subject'] = "Zimbra : Error with User synchronisation"
        msg['From'] = smtp_sender
        msg['To'] = smtp_recipient
        s = smtplib.SMTP(smtp_host)
        s.sendmail(smtp_sender,smtp_recipient,msg.as_string())


def report(in_msg):
        if not send_mail:
                return
        msg = MIMEText(in_msg,'plain','utf-8')
        msg['Subject'] = "Zimbra : Provisionning Utilisateur %s-%s-%s %s:%s" % (heure.day, heure.month, heure.year, heure.hour, heure.minute)
        msg['From'] = smtp_sender
        msg['To'] = smtp_recipient
        s = smtplib.SMTP(smtp_host)
        s.sendmail(smtp_sender,smtp_recipient,msg.as_string())

def ldapZIMBRAconn():
#
# LDAP Connection
#
        try:
                ldap_conn = ldap.initialize(ldapZIMBRA_protocol+ldap_ZIMBRA1+':'+str(ldap_portZIMBRA)+'/')
                ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
                ldap_conn.simple_bind_s(ldap_ZIMBRAuser,ldap_ZIMBRApass)
        except ldap.LDAPError as e:
                err_report('Problem with ldap connexion : %s %s' %(e,ldap_ZIMBRA1))
                exit()

        ldap_result_id = ldap_conn.search( ldap_ZIMBRAbase_dn, ldap.SCOPE_SUBTREE,'(&(!(objectClass=zimbraCalendarResource))(!(zimbraNotes=no_ad_user))(!(zimbraIsSystemAccount=TRUE))(objectClass=zimbraAccount)(!(zimbraAccountStatus=closed)))',['cn','zimbraMailDeliveryAddress','description','givenName','sn','cn','displayName','title','telephoneNumber'])
        result_type, result_data = ldap_conn.result(ldap_result_id)
        return result_type, result_data , ldap_conn


def ldapconn():
#
# LDAP Connection
#
	try:
        	ldap_conn = ldap.initialize(ldap_protocol+ldap_host1+':'+str(ldap_port)+'/')
		ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
	        ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
        	ldap_conn.simple_bind_s(ldap_user,ldap_pass)
	except ldap.LDAPError as e:
        	err_report('Problem with ldap connexion : %s %s' %(e,ldap_host1))
        	try :
                	ldap_conn = ldap.initialize(ldap_protocol+ldap_host2+':'+str(ldap_port)+'/')
        	        ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
                	ldap_conn.simple_bind_s(ldap_user,ldap_pass)
        	except ldap.LDAPError as e:
                	err_report('Problem with ldap connexion : %s %s' %(e,ldap_host2))
                	exit()
	ldap_result_id = ldap_conn.search( ldap_base_dn, ldap.SCOPE_SUBTREE,'(&(!(UserAccountControl:1.2.840.113556.1.4.803:=2))(objectClass=person)(mail=*@ville-goussainville.fr))',['cn','mail'])
        result_type, result_data = ldap_conn.result(ldap_result_id)
	return result_type, result_data , ldap_conn


def createuser(result_type,result_data,ldap_conn,zimbra_user,f):
	userldap = []
	for user in result_data:
	        if user[0] is not None:
			userldap.append(user[1]['mail'][0].lower())
	                if user[1]['mail'][0].lower() not in zimbra_user:
				# Création des utilisateurs non existant dans zimbra
				mail = str((user[1]['mail'][0]))
	                        if verbose:
	                                print("[+] Add : "+mail)
				report_mail.append("[+] Add : "+mail)
	                        #Construction des attribus pour la requete ldap
	                        ad_list_attr=[]
	                        for attr in list_attr:
	                                ad_list_attr.append(attr)
	                        ldap_result_id = ldap_conn.search( ldap_base_dn, ldap.SCOPE_SUBTREE,'mail='+mail,ad_list_attr)
	                        user_result_type, user_result_data = ldap_conn.result(ldap_result_id)
	                        add_attr=""
	                        for attr in list_attr: #Ajout des attribus disponible au zimbra
	                                try:
	                                        add_attr+=" "+list_attr[attr]+" \""+str(user_result_data[0][1][attr][0])+"\""
	                                except:
						report_mail.append("Error with attributes "+attr+" for "+mail)
	                                        if verbose:
        	                                        print("Error with attributes "+attr+" for "+mail)
	                        try:
					commands.getstatusoutput("/opt/zimbra/bin/zmprov ca " +mail+" JEhDJennujg73H3761203P92undhdge7372362G2302IEpassword "+add_attr)
                	                #f.write("ma "+mail+" zimbraMailTransport 'smtp:mailclean.anact.fr:25'  \n")
        	                except:
					
					report_mail.append("Error with :"+mail)
	                                print("Error with :"+mail)
			else:
				# Modification des utilisateur existant si leur fiche a été modifié dans le dernier quart d'heures
				#On recupere un variable daté du dernier quart d'heure au format ldap
				now = datetime.utcnow() - timedelta(minutes=120)
				lastchange = now.strftime("%Y%m%d%H%M%S.0Z")
				ad_list_attr=[]
		
				#Construction des attribus pour la requete ldap
				mail = str((user[1]['mail'][0]))
				for attr in list_attr:
                                        ad_list_attr.append(attr)
				 #Construction des attribus pour la requete ldap
				ldap_result_id = ldap_conn.search( ldap_base_dn, ldap.SCOPE_SUBTREE,'(&(mail='+mail+')(whenChanged>='+lastchange+'))',ad_list_attr)
				#ldap_result_id = ldap_conn.search( ldap_base_dn, ldap.SCOPE_SUBTREE,'(mail='+mail+')',ad_list_attr)
				user_result_type, user_result_data =  ldap_conn.result(ldap_result_id)
				add_attr=""
				if  len(user_result_data) > 3:
					for attr in ad_list_attr:
                                       		try:
                                                	add_attr+=" "+list_attr[attr]+" \""+str(user_result_data[0][1][attr][0])+"\""
                                        	except:
							report_mail.append("Error with attributes "+attr+" for "+mail)
                                                	if verbose:
                                                        	print("Error with attributes "+attr+" for "+mail)

					try:
						report_mail.append("[+] Modify : "+mail)
                                		if verbose:
                                        		print("[+] Modify : "+mail)
                                        	f.write("ma "+mail+" "+add_attr+"\n")
                                        #	f.write("sm "+mail+" cm /GAL galsync@anact.fr /_InternalGAL \n")
                                	except:
						report_mail.append("Error with :"+mail)
                                        	print("Error with :"+mail)
	return userldap


def SupprUser(result_data,zimbra_user,userldap,f):
	for user in zimbra_user:
		if not any(user in ldap for ldap in userldap):
			if user.find('virus') == -1 and user.find('galsync') == -1 and user.find('spam.') == -1  and  user.find('ham.') == -1 and  user.find('admin') == -1 and  user.find('wiki') == -1:
				# Supression des utilisateur non present dans le LDAP
				
				report_mail.append("[-] Del : "+user)
				if verbose:
                                        print("[-] Del : "+user)
				f.write("ma " +user+" description '"+str(heure.day)+"-"+str(heure.month)+"-"+str(heure.year)+" "+str(heure.hour)+":"+str(heure.minute)+"'  zimbraAccountStatus closed zimbraHideInGAL TRUE \n")

#On recupere la liste des utilisateur

status,output = commands.getstatusoutput("/sbin/ip addr | grep inet")
if '10.10.0.2' not in output:
	exit()

f = open(zmprov_file,"w")
zimbra_uid = {}
result_type, result_data , ldap_conn = ldapconn()
result_type, result_dataZIMBRA , ldap_connZIMBRA = ldapZIMBRAconn()
for uid in result_dataZIMBRA:
        try:
                zimbra_uid[uid[1]['zimbraMailDeliveryAddress'][0]] = uid[1]['zimbraMailDeliveryAddress'][0]
        except:
		zimbra_error[uid[1]['zimbraMailDeliveryAddress'][0]] = 'error'
                print 'Error with user '+uid[1]['zimbraMailDeliveryAddress'][0]

#Creation / modification des utilisateurs
userldap = createuser(result_type,result_data,ldap_conn,zimbra_uid,f)
#Suppresion des utilisateurs non present dans le LDAP
SupprUser(result_data,zimbra_uid,userldap,f)
f.close()

if os.stat(zmprov_file).st_size > 0:
        report_mail = '\n'.join(report_mail)
        report(report_mail)
#	status,output = commands.getstatusoutput("/opt/zimbra/bin/zmprov -f " + zmprov_file)
	err_report(output)


