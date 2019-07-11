#!/usr/bin/python
# -*- encoding: utf-8 -*-

"""


This script allows you to create/delete and list child accound in zimbra


"""


import os,sys,commands,argparse,ldap

ldap_protocol = 'ldap://'
ldap_port = 389
ldap_ZIMBRA1 = ''
ldap_ZIMBRAuser = 'uid=zmreplica,cn=admins,cn=zimbra'
ldap_ZIMBRApass = ''
ldap_ZIMBRAbase_dn=''
ldap_portZIMBRA = 389



zmprov= open("/var/local/zmprov","w")


def ldapZIMBRAconn():
#
# LDAP Connection
#
        try:
                ldap_conn = ldap.initialize(ldap_protocol+ldap_ZIMBRA1+':'+str(ldap_portZIMBRA)+'/')
                ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
                ldap_conn.simple_bind_s(ldap_ZIMBRAuser,ldap_ZIMBRApass)
        except ldap.LDAPError as e:
                err_report('Problem with ldap connexion : %s %s' %(e,ldap_ZIMBRA1))
                exit()
        ldap_result_id = ldap_conn.search( ldap_ZIMBRAbase_dn, ldap.SCOPE_SUBTREE,'(&(!(objectClass=zimbraCalendarResource))(!(description=no_ad_user))(!(zimbraIsSystemAccount=TRUE))(zimbraACE=*sendOnBehalfOf)(!(zimbraAccountStatus=closed)))',['cn','zimbraMailDeliveryAddress','description','givenName','sn','cn','displayName','Zimbraid','zimbraACE'])
        result_type, result_data = ldap_conn.result(ldap_result_id)
        return result_type, result_data , ldap_conn


def listchild():
        print "###################### LISTE DES COMPTES DELEGUES ######################"
        result_type, result_dataZIMBRA , ldap_conn = ldapZIMBRAconn()
        for user in result_dataZIMBRA:
                for master in user[1]['zimbraACE']:
                        if 'sendOnBehalfOf' in  master:
                                id=master.split(' ')
                                ldap_result_id = ldap_conn.search( ldap_ZIMBRAbase_dn, ldap.SCOPE_SUBTREE,'(Zimbraid='+id[0]+')',['cn','zimbraMailDeliveryAddress'])
                                user_result_type, user_result_data =  ldap_conn.result(ldap_result_id)
                                print
                                print "Compte maitre : "+ user_result_data[0][1]['zimbraMailDeliveryAddress'][0]
                                print  "Compte Délégué : "+ user[1]['zimbraMailDeliveryAddress'][0]
                                print

def createchild(child,account,user_id):
	status,output = commands.getstatusoutput("""/opt/zimbra/bin/zmmailbox -z -m """+child+""" gaf | grep "Inbox" | awk -F" "  '{print "sm """+child+""" mff "$1" u"}' | zmprov""")
	status,output = commands.getstatusoutput("""/opt/zimbra/bin/zmmailbox -z -m """+child+""" gaf | grep "Sent" | awk -F" "  '{print "sm """+child+""" mff "$1" u"}' | zmprov""")
        zmprov.write("sm  "+str(child)+" mfg / account "+str(account)+" rwixda\n")
        zmprov.write("sm "+str(account)+"  createMountpoint /"+str(child) +" "+str(child)+" /\n")
        zmprov.write("ma "+child+" +zimbraACE '"+user_id[1]+" usr sendOnBehalfOf'\n")
        zmprov.write("ma "+child+" +zimbraACE '"+user_id[1]+" usr sendAs'\n")

def supprchild(child,account,user_id):
        zmprov.write("sm "+str(child)+" mfg / account "+str(account)+" none\n")
        zmprov.write("sm "+str(account)+"  df /"+str(child) +"\n")
        zmprov.write("ma "+child+" -zimbraACE '"+user_id[1]+" usr sendOnBehalfOf'\n")
        zmprov.write("ma "+child+" -zimbraACE '"+user_id[1]+" usr sendAs'\n")


def Account_existe(account):
        status,output = commands.getstatusoutput("/opt/zimbra/bin/zmprov ga "+account+ " | grep 'zimbraId:'")
        user_id = output.split('\n')
        user_id = user_id[0].split(" ")
        if "account.NO_SUCH_ACCOUNT" == user_id[1]:
                print "Le compte primaire  n'existe pas"
                exit()
        return user_id

def Child_existe(child):
        status,output = commands.getstatusoutput("/opt/zimbra/bin/zmprov ga "+child+ " | grep 'zimbraId:'")
        child_id = output.split('\n')
        child_id = child_id[0].split(" ")
        if "account.NO_SUCH_ACCOUNT" == child_id[1]:
                print "Le compte délégué n'existe pas "
                exit()
        return child_id

parser = argparse.ArgumentParser(description='Script de création de child account')
parser.add_argument("-l","--liste", help="Liste l'ensemble des comptes délégué",action='store_true')
parser.add_argument("-m","--mail", help="adresse mail de l'utilisateur primaire",required=False)
parser.add_argument("-c","--child", help="adresse mail de l'utilisateur délégué",required=False)
parser.add_argument("-d","--delete", help="Suppresion du child account",action='store_true')
args = parser.parse_args()
account=args.mail
child=args.child
if account == None and  child == None and args.liste == False:
        parser.print_help()
        exit()
elif args.liste == True:
        listchild()
        exit()
elif account == None or  child == None:
        parser.print_help()
        exit()



if account==child:
        print "Impossible de délégué un compte sur lui même"
        exit()
if args.liste == True:
        print 'tototo'
        exit()


user_id=Account_existe(account)
child_id=Child_existe(child)
if args.delete==False:
        createchild(child,account,user_id)
elif args.delete==True:
        supprchild(child,account,user_id)
zmprov.close()
status,output = commands.getstatusoutput("/opt/zimbra/bin/zmprov -f /var/local/zmprov")
