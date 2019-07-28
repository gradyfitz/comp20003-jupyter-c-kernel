NBGRADER_CONFIG_PY="# NBGrader configuration file.

c = get_config()
# Course ID, you can change this for a different course.
c.Exchange.course_id = 'COMP20003'
# Path to exchange on shared volume.
c.Exchange.root = '/home/shared/exchange'
# Set up C kernel code stub replacement.
c.ClearSolutions.code_stub = {
  'c': '/* Your code here */',
  'python': '# Your code here\nraise NotImplementedError'
}
# The timeout for executions.
c.ExecutePreprocessor.timeout = 60
"

echo "$NBGRADER_CONFIG_PY" > $1/nbgrader_config.py
