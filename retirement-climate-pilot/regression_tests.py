#!/usr/bin/env python3
"""Isolated negative regression tests of V1.6 execution gates. Never touches real RUN_STATE."""
import copy,importlib.util,json,pathlib,tempfile,unittest

MODULE=pathlib.Path("retirement-climate-pilot/assault_state.py")
spec=importlib.util.spec_from_file_location("assault_state",MODULE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REAL_STATE=json.loads(m.STATE.read_text(encoding="utf-8"))
REAL_LOG=m.LOG.read_text(encoding="utf-8")
REAL_CURRENT=m.CURRENT.read_text(encoding="utf-8")
class AssaultGateRegression(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.orig=(m.STATE,m.LOG,m.CURRENT,m.OUTPUT,m.STATUS,m.ACTION,m.RUN_ID,m.SOURCE_NAME)
        self.addCleanup(self.restore)
        self.root=pathlib.Path(self.temp.name)
        m.STATE=self.root/"RUN_STATE.json";m.LOG=self.root/"RUN_LOG.jsonl"
        m.CURRENT=self.root/"CURRENT_STATE.md";m.OUTPUT=self.root/"output"
        m.STATUS=self.root/"status.json";m.ACTION="RET-SPATIAL-001"
        m.SOURCE_NAME="spatial_probe.json";m.RUN_ID="SYNTHETIC-REGRESSION"
        m.OUTPUT.mkdir()
        m.LOG.write_text(REAL_LOG,encoding="utf-8")
        m.CURRENT.write_text(REAL_CURRENT,encoding="utf-8")
        self.s=copy.deepcopy(REAL_STATE)
        self.s["current_state_ref"]["git_blob_sha"]=m.blob_sha(m.CURRENT)
        self.s["writeback_verification"]={"status":"POSTCHECK_PASS"}
        self.s["active_action"]={"action_id":"RET-SPATIAL-001","status":"READY"}
        self.save()
    def restore(self):
        (m.STATE,m.LOG,m.CURRENT,m.OUTPUT,m.STATUS,m.ACTION,m.RUN_ID,m.SOURCE_NAME)=self.orig
    def save(self):
        m.emit_json(m.STATE,self.s)
    def test_missing_state_must_block(self):
        m.STATE.unlink()
        with self.assertRaisesRegex(RuntimeError,"STATE_MISSING"):m.load_state()
    def test_stale_version_must_block(self):
        self.s["current_state_ref"]["git_blob_sha"]="0"*40;self.save()
        with self.assertRaisesRegex(RuntimeError,"STATE_DRIFT"):m.load_state()
    def test_missing_unique_action_must_block(self):
        self.s["active_action"]={};self.save()
        with self.assertRaisesRegex(RuntimeError,"NO_ACTION"):m.precheck()
    def test_unverified_previous_write_must_block(self):
        self.s["writeback_verification"]={"status":"PENDING_REMOTE_CHECK"};self.save()
        with self.assertRaisesRegex(RuntimeError,"PREVIOUS_WRITEBACK_UNVERIFIED"):m.precheck()
    def test_completed_not_inferred_as_research_delta(self):
        m.precheck()
        m.emit_json(m.OUTPUT/m.SOURCE_NAME,{"status":"BLOCKED_WITH_EVIDENCE","error":"synthetic download error","valid_county_screenings":0})
        m.finalize()
        d=json.loads(m.STATE.read_text(encoding="utf-8"))
        self.assertEqual(d["last_verified_run"]["research_delta_status"],"BLOCKED_WITH_EVIDENCE")
        self.assertEqual(d["last_verified_run"]["engineering_status"],"FAIL")
        self.assertNotEqual(d["writeback_verification"]["status"],"POSTCHECK_PASS")
    def test_duplicate_result_id_fails(self):
        self.s["closed_result_refs"]=["RESULT-ONE","RESULT-ONE"];self.save()
        with self.assertRaises(AssertionError):m.selftest()
if __name__=="__main__":unittest.main(verbosity=2)
