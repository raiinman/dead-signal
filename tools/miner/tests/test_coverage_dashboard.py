import tempfile,unittest
from pathlib import Path
from dead_signal_coverage_dashboard import build_coverage_dashboard
class CoverageDashboardTests(unittest.TestCase):
 def test_field_counts_and_states_are_separate(self):
  weapons=[{'rarity':{'state':'resolved-installed-game'},'description':{'state':'resolved-installed-game'},'ranged_stats':{'projectile_count':5},'handling':{'state':'resolved-installed-game'},'firing_mode':{'label_state':'resolved-installed-enum'},'compatibility':{'cradle':{'state':'unresolved'}},'special_skill':{'text':'Skill'}},{'rarity':{'state':'unresolved'},'description':{'state':'unresolved'},'ranged_stats':None,'compatibility':{'cradle':{'state':'exact','candidate_count':2}},'special_skill':{'resolution':{'status':'pending'}}}]
  with tempfile.TemporaryDirectory() as t:
   r=build_coverage_dashboard({'weapons':weapons},Path(t));by={x['field']:x for x in r['fields']};self.assertEqual('1/2',by['Rarity']['display']);self.assertEqual('1/1',by['Projectile semantics']['display']);self.assertEqual(1,by['Special Skill']['states']['unresolved evidence state']);self.assertTrue((Path(t)/'dead-signal-coverage-dashboard.json').is_file())
if __name__=='__main__':unittest.main()
