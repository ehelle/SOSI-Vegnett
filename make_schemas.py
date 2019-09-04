import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import re
import csv

baseUrl = "http://skjema.geonorge.no/SOSI/generelleKonsepter/generelleTyper/5.0/"
feature2xml = {
    "kvalitet.Posisjonskvalitet.målemetodeHøyde": "MålemetodeHøyde.xml",
    "kvalitet.Posisjonskvalitet.målemetode": "Målemetode.xml",
    "kvalitet.Posisjonskvalitet.synbarhet": "Synbarhet.xml"
}
with open("Mappingtabeller/posisjonskvalitet.csv", mode = "w") as csv_file:
    wrt = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    for f in feature2xml:
        url = baseUrl + urllib.parse.quote(feature2xml[f])
        print(url)
        response = urllib.request.urlopen(url)
        rawxml = response.read().decode('utf-8')
        xmlstring = re.sub(' xmlns="[^"]+"', '', rawxml, count=1) # remove namespace
        #print(xml)
        root = ET.fromstring(xmlstring)

        for child in root:
            #print("--", child.tag, child.attrib)
            for child2 in child:
                pass
                #print("----", child2.tag, child2.attrib)

        for val in root.findall('dictionaryEntry'):
            if feature2xml[f] == "Synbarhet.xml":
                sosinavn = val[0][3].text
                num = val[0][1].text    
            else:
                sosinavn = val[0][1].text
                num = val[0][3].text
                num = re.sub('SOSI_verdi:', '', num, count=1)

            wrt.writerow([f, num, sosinavn])

            #ident = val.find('identifier').text
            #print(ident)
    


