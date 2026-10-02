import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

class CommunityApplicationsIntegrityTests(unittest.TestCase):
    def test_profile_schema(self):
        root=ET.parse('ca_profile.xml').getroot()
        self.assertEqual(root.tag,'CommunityApplications')
        profile=(root.findtext('Profile') or '').strip()
        self.assertTrue(profile)

    def test_docker_template_schema(self):
        path=Path('hevy-progress.xml')
        root=ET.parse(path).getroot()
        self.assertEqual(root.tag,'Container')
        self.assertEqual(root.attrib.get('version'),'2')
        required=['Name','Repository','Network','Overview','Project','TemplateURL','Category','WebUI','Icon']
        for tag in required:
            self.assertTrue((root.findtext(tag) or '').strip(),tag)
        self.assertEqual(root.findtext('Repository'),'ghcr.io/utgard21/hevy-sync:latest')
        self.assertEqual(root.findtext('Registry'),'https://ghcr.io/utgard21/hevy-sync')
        self.assertEqual(root.findtext('Category'),'Tools:System')
        self.assertEqual(
            root.findtext('TemplateURL'),
            'https://raw.githubusercontent.com/Utgard21/Hevy-sync/main/hevy-progress.xml'
        )
        configs=root.findall('Config')
        self.assertTrue(any(c.attrib.get('Type')=='Port' and c.attrib.get('Target')=='8080' for c in configs))
        self.assertTrue(any(c.attrib.get('Type')=='Path' and c.attrib.get('Target')=='/data' for c in configs))

    def test_only_expected_ca_xml_files(self):
        xmls=sorted(str(p).replace('\\\\','/') for p in Path('.').rglob('*.xml'))
        self.assertEqual(xmls,['ca_profile.xml','hevy-progress.xml'])

if __name__=='__main__':
    unittest.main()
