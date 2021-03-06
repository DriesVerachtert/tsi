import io
import logging
import os
import unittest
import uuid
import slurm.BSS
import MockConnector
from lib import TSI

basedir = os.getcwd()
    
class TestBSSSlurm(unittest.TestCase):
    def setUp(self):
        # setup logger
        self.LOG = logging.getLogger("tsi.testing")
        self.LOG.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.LOG.handlers = [ch]
        self.bss = slurm.BSS.BSS()

    def test_init(self):
        config = {'tsi.testing': True}
        self.bss.init(config, self.LOG)
        self.assertTrue(config['tsi.submit_cmd'] is not None)

    def test_parse_qstat(self):
        os.chdir(basedir)
        with open("tests/input/qstat_slurm.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("182867 RUNNING large\n" in result)
        self.assertTrue("182917 RUNNING batch\n" in result)
        self.assertTrue("182588 QUEUED batch\n" in result)
        self.assertTrue("182732 RUNNING large\n" in result)
        self.assertTrue("182744 QUEUED large\n" in result)
        self.assertTrue("182745 RUNNING small\n" in result)
        self.assertTrue("182800 COMPLETED small\n" in result)

    def test_extract_job_id(self):
        os.chdir(basedir)
        reply = "Submitted job 123"
        result = self.bss.extract_job_id(reply)
        self.assertTrue("123" in result)
        reply = "Error 123"
        result = self.bss.extract_job_id(reply)
        self.assertTrue(result is None)

    def has_directive(self, cmds, name, value=None):
        result = False
        for line in cmds:
            if line.startswith(name):
                if value:
                    result=value in line
                else:
                    result=True
                break
        return result

    def test_create_submit_script(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 'Submitted batch job 1234'"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_STDOUT stdout
#TSI_STDERR stderr
#TSI_SCRIPT
#TSI_QUEUE fast
#TSI_PROJECT myproject
#TSI_TIME 60
#TSI_MEMORY 32
#TSI_NODES 1
#TSI_PROCESSORS_PER_NODE 64
#TSI_ARRAY 10
#TSI_ARRAY_LIMIT 2
#TSI_BSS_NODES_FILTER NONE
#TSI_JOBNAME test_job
#TSI_SCRIPT
echo "Hello World!"
sleep 3
ENDOFMESSAGE
""" % (uspace, uspace)
        submit_cmds = self.bss.create_submit_script(msg, config, self.LOG)
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --partition", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --nodes", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --ntasks-per-node", "64"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --mem", "32"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --time", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --array", "10%2"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --account", "myproject"))
        self.assertFalse(self.has_directive(submit_cmds, "#SBATCH --constraint"))


    def test_submit_nodes_filter(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 'Submitted batch job 1234'"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_STDOUT stdout
#TSI_STDERR stderr
#TSI_QUEUE fast
#TSI_PROJECT myproject
#TSI_TIME 60
#TSI_MEMORY 32
#TSI_NODES 1
#TSI_PROCESSORS_PER_NODE 64
#TSI_ARRAY 10
#TSI_ARRAY_LIMIT 2
#TSI_BSS_NODES_FILTER gpu
#TSI_SCRIPT
echo "Hello World!"
sleep 3
ENDOFMESSAGE
""" % (uspace, uspace)
        submit_cmds = self.bss.create_submit_script(msg, config, self.LOG)
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --partition", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --nodes", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --ntasks-per-node", "64"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --mem", "32"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --time", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --array", "10%2"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --account", "myproject"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --constraint", "gpu"))


    def test_submit_raw(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 'Submitted batch job 1234'"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        with open(uspace+"/foo.sh", "w") as f:
            f.write("""#!/bin/bash
#SLURM --myopts
            """)
        
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE raw
#TSI_JOB_FILE foo.sh
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
ENDOFMESSAGE
""" % (uspace, uspace)
                
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        
        self.bss.submit(msg,connector, config, self.LOG)
        result = control_out.getvalue()
        assert "1234" in result
        os.chdir(cwd)

        
    def test_submit_normal(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 'Submitted batch job 1234'"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE normal
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_SCRIPT
echo "Hello World!"

ENDOFMESSAGE
""" % (uspace, uspace)
                
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        
        self.bss.submit(msg,connector, config, self.LOG)
        result = control_out.getvalue()
        assert "1234" in result
        os.chdir(cwd)


    def test_submit_fail(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "/bin/false"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
ENDOFMESSAGE
""" % (uspace, uspace)
                
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        
        self.bss.submit(msg,connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        assert "TSI_FAILED" in result
        os.chdir(cwd)

    def test_parse_details(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        with open("tests/input/details_slurm.txt", "r") as f:
            raw = f.read()
        parsed = self.bss.parse_job_details(raw)
        print(parsed)

    def test_report_details(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        config['tsi.details_cmd'] = "cat "    
        TSI.setup_defaults(config)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        msg = "#TSI_BSSID tests/input/details_slurm.txt\n"
        self.bss.get_job_details(msg, connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)


if __name__ == '__main__':
    unittest.main()
