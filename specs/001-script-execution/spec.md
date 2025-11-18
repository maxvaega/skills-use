# Feature Specification: Script Execution Support

**Feature Branch**: `001-script-execution`
**Created**: 2025-01-17
**Status**: Draft
**Input**: User description: "Script execution support for skills - Enable skills to bundle executable scripts (Python, Shell, JavaScript, etc.) that agents can invoke for deterministic operations"

## Clarifications

### Session 2025-01-17

- Q: When are scripts detected in the progressive disclosure loading pattern? → A: During skill invocation (lazy, when the skill is first used) - scripts are detected after content is loaded but before execution
- Q: After scripts are detected during skill invocation, how are they made available to the agent for execution in LangChain? → A: Each detected script becomes a separate StructuredTool (e.g., skill "pdf-extractor" with 3 scripts generates 3 tools: "pdf-extractor.extract", "pdf-extractor.convert", "pdf-extractor.parse")
- Q: What happens to the skill's prompt-based StructuredTool when scripts are detected? → A: The prompt tool remains (if prompt exists) AND script tools are added (skill can have multiple tools: one for prompt, N for scripts)
- Q: What input schema should script-based StructuredTools declare to the LangChain agent? → A: Free-form JSON object (single field accepting any JSON, script receives whatever agent provides)
- Q: How should script-based StructuredTools describe their purpose to the agent? → A: Extract description from script's first comment/docstring (parse first block of #, //, or """ comments); if no docstring exists, leave description blank (skill content is expected to be sufficiently explanatory)
- Q: When an agent invokes a script tool, what should the StructuredTool's function implementation do with the return value from script execution? → A: Return stdout as content if exit_code==0, else raise exception with stderr as message; format: {"type": "tool_result", "tool_use_id": "<id>", "content": "string | list | null", "is_error": false | true}
- Q: How are arguments passed to scripts when the agent invokes them? → A: Arguments are passed as JSON via stdin (scripts must read and parse JSON from standard input)
- Q: How does the system determine which interpreter to use for each script type? → A: Extension-based mapping with fallback to shebang line (e.g., `.py` → `python3`, `.sh` → `bash`, `.js` → `node`, then check shebang if needed)
- Q: How does the system handle scripts that produce extremely large output (e.g., 100MB to stdout)? → A: Capture up to a size limit (10MB), then truncate with warning logged
- Q: What should the system do when a script path contains spaces or special characters (e.g., `scripts/my script.py` or `scripts/file[1].py`)? → A: Allow all characters except path separators (.., /, \); rely on FilePathResolver validation
- Q: How should the system handle scripts that crash with segmentation faults or other signals (e.g., SIGKILL, SIGSEGV)? → A: Return negative exit code (e.g., -11 for SIGSEGV), stderr="Signal: SIGSEGV", log as ERROR
- Q: How should the system handle concurrent script executions from the same skill (e.g., agent invokes same script multiple times in parallel)? → A: Allow concurrent executions (each gets independent subprocess, no shared state)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute Skill Scripts for Deterministic Processing (Priority: P1)

As a user interacting with an AI agent, I want skills to perform deterministic operations (like PDF text extraction, data transformation, or file format conversion) so that I get reliable, accurate results beyond what LLM inference can provide.

**Why this priority**: This is the core value proposition. Skills need to execute scripts to deliver deterministic, computation-heavy operations that LLMs cannot reliably perform.

**Independent Test**: Can be fully tested by creating a simple skill with a Python script, invoking it with test data, and verifying the output is captured and returned to the agent correctly. Delivers immediate value by enabling computational capabilities.

**Acceptance Scenarios**:

1. **Given** a skill with a Python script in `scripts/extract.py`, **When** the agent invokes the skill with arguments `{"file_path": "/path/to/doc.pdf"}` passed as JSON via stdin, **Then** the script executes with the skill's base directory as working directory, receives the JSON via stdin, captures stdout/stderr, and returns the output to the agent
2. **Given** a skill script that performs data transformation, **When** the script completes successfully (exit code 0), **Then** the transformed data is available in stdout for the agent to use
3. **Given** a skill script that fails with an error, **When** the script exits with non-zero code, **Then** the error message from stderr is captured and returned to the agent for error handling
4. **Given** a skill with nested scripts in `scripts/utils/parser.py`, **When** the agent invokes the nested script, **Then** the script path is resolved correctly relative to the skill base directory
5. **Given** a script that crashes with a segmentation fault (SIGSEGV), **When** the script execution completes, **Then** exit_code is -11, stderr contains "Signal: SIGSEGV", and an ERROR log entry is created with signal details

---

### User Story 2 - Safe Script Execution with Security Boundaries (Priority: P1)

As a system administrator, I want script execution to respect security boundaries so that malicious skills cannot access files outside their directory or escalate privileges.

**Why this priority**: Security is non-negotiable. Without proper security controls, script execution could expose serious vulnerabilities.

**Independent Test**: Can be fully tested by attempting path traversal attacks (e.g., `../../etc/passwd`), verifying they're blocked with appropriate errors, and confirming all executions are logged for auditing.

**Acceptance Scenarios**:

1. **Given** a skill script attempts to access `../../etc/passwd`, **When** the path is validated before execution, **Then** a PathSecurityError is raised and the execution is blocked with security violation logged
2. **Given** a skill script has setuid or setgid permissions, **When** the script is validated before execution, **Then** a ScriptPermissionError is raised and the script is rejected
3. **Given** any script execution, **When** the script completes (success or failure), **Then** an audit log entry is created with timestamp, skill name, script path, arguments (truncated), exit code, and execution time
4. **Given** a script with a symlink pointing outside the skill directory, **When** the symlink is resolved, **Then** a PathSecurityError is raised and execution is blocked

---

### User Story 3 - Timeout Management for Long-Running Scripts (Priority: P1)

As an agent developer, I want scripts to respect execution timeouts so that infinite loops or hung processes don't block the agent indefinitely.

**Why this priority**: Without timeouts, a single misbehaving script could hang the entire agent system, making this critical for reliability.

**Independent Test**: Can be fully tested by creating a script with an infinite loop, setting a 5-second timeout, and verifying the process is killed after 5 seconds with appropriate timeout error.

**Acceptance Scenarios**:

1. **Given** a script with an infinite loop and default timeout of 30 seconds, **When** the script is executed, **Then** the process is killed after 30 seconds with exit code 124 and stderr message "Timeout"
2. **Given** a custom timeout configuration of 60 seconds, **When** a long-running script is executed, **Then** the timeout is respected at 60 seconds instead of default 30 seconds
3. **Given** a script that times out, **When** the timeout occurs, **Then** a WARNING log entry is created with details about the timeout
4. **Given** a script that completes within the timeout, **When** execution finishes, **Then** the actual execution time is measured and returned in milliseconds

---

### User Story 4 - Tool Restriction Enforcement for Scripts (Priority: P2)

As a skill author, I want to declare which tools my skill can use (including Bash for scripts) so that users know the skill's capabilities and limitations upfront.

**Why this priority**: Tool restrictions provide transparency and control, but the feature still works without them. This is important for trust but not blocking for basic functionality.

**Independent Test**: Can be fully tested by creating two skills - one with `allowed-tools: Bash, Read` (allowed) and one with `allowed-tools: Read, Write` (blocked) - and verifying script execution succeeds for the first and raises ToolRestrictionError for the second.

**Acceptance Scenarios**:

1. **Given** a skill with `allowed-tools: Bash, Read, Write`, **When** the agent attempts to execute a script, **Then** execution proceeds successfully because Bash is in the allowed list
2. **Given** a skill with `allowed-tools: Read, Write` (no Bash), **When** the agent attempts to execute a script, **Then** a ToolRestrictionError is raised with message "Tool 'Bash' not allowed for skill..."
3. **Given** a skill with no `allowed-tools` specified (null/empty), **When** the agent attempts to execute a script, **Then** execution proceeds successfully (no restrictions)
4. **Given** a tool restriction error, **When** the error is raised, **Then** the error message includes the skill name and list of allowed tools for debugging

---

### User Story 5 - Environment Context for Scripts (Priority: P2)

As a skill author, I want my scripts to have access to skill metadata (name, base directory, version) so that scripts can locate supporting files and provide context-aware logging.

**Why this priority**: Environment context improves script reliability and debugging, but scripts can function without it. This is valuable but not critical for MVP.

**Independent Test**: Can be fully tested by creating a script that prints environment variables (SKILL_NAME, SKILL_BASE_DIR, SKILL_VERSION, SKILLKIT_VERSION) and verifying all values are correctly injected.

**Acceptance Scenarios**:

1. **Given** a skill named "pdf-extractor" version "1.0.0", **When** its script is executed, **Then** environment variables SKILL_NAME="pdf-extractor" and SKILL_VERSION="1.0.0" are available to the script
2. **Given** a skill at path `/home/user/.claude/skills/pdf-extractor`, **When** its script is executed, **Then** environment variable SKILL_BASE_DIR="/home/user/.claude/skills/pdf-extractor" is available
3. **Given** skillkit library version 0.3.0, **When** any script is executed, **Then** environment variable SKILLKIT_VERSION="0.3.0" is available to the script
4. **Given** a script that reads `./data/config.yaml` using SKILL_BASE_DIR, **When** the script constructs the path as `$SKILL_BASE_DIR/data/config.yaml`, **Then** the file is successfully located and read

---

### User Story 6 - Automatic Script Detection (Priority: P3)

As a skill author, I want my scripts to be automatically discovered so that I don't need to manually register each script file.

**Why this priority**: This is a convenience feature that improves developer experience but isn't required for basic functionality. Scripts can be referenced explicitly without detection.

**Independent Test**: Can be fully tested by creating a skill with multiple scripts in different locations (scripts/, scripts/utils/, root), triggering detection, and verifying all executable scripts are found with correct metadata.

**Acceptance Scenarios**:

1. **Given** a skill with scripts in `scripts/extract.py`, `scripts/convert.sh`, and `scripts/utils/parser.py`, **When** the skill is invoked for the first time (triggering lazy script detection), **Then** all three scripts are detected with correct relative paths
2. **Given** a skill with non-executable files like `data/config.yaml` and `README.md`, **When** script detection runs during skill invocation, **Then** these files are excluded from detection
3. **Given** a skill with 50 scripts, **When** the skill is invoked and script detection runs, **Then** detection completes in under 10 milliseconds
4. **Given** a script file with extension `.py`, `.sh`, `.js`, `.rb`, or `.pl`, **When** detection runs during skill invocation, **Then** the file is identified as executable and the script type is determined from the extension

---

### Edge Cases

- **Script paths with spaces or special characters** (e.g., `scripts/my script.py`, `scripts/file[1].py`): All characters are allowed except path separators (.., /, \); FilePathResolver validates the final resolved path is within the skill base directory regardless of filename characters
- **Scripts that crash with segmentation faults or other signals** (SIGKILL, SIGSEGV, etc.): Return negative exit code matching the signal number (e.g., -11 for SIGSEGV), set stderr to "Signal: <SIGNAL_NAME>", and log as ERROR level with signal details for debugging
- **Concurrent script executions from the same skill**: Each execution gets an independent subprocess with no shared state; multiple parallel invocations are supported without locking or serialization (subprocess module is thread-safe)
- What happens when a script is deleted or moved while the skill is loaded in memory?
- What happens when the working directory doesn't have write permissions?
- What happens when environment variables exceed system limits?
- How does the system handle scripts on different platforms (Windows vs Unix)?
- What happens when arguments cannot be serialized to JSON (e.g., circular references, non-JSON-serializable objects)?
- How does the system handle scripts that don't read from stdin or fail to parse the JSON input?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST execute scripts within the skill's base directory as the working directory
- **FR-002**: System MUST capture stdout, stderr, exit code, and execution time for all script executions; stdout and stderr are each captured up to 10MB, beyond which output is truncated with a WARNING log entry; for scripts terminated by signals (SIGSEGV, SIGKILL, etc.), exit_code is set to negative signal number (e.g., -11 for SIGSEGV), stderr is set to "Signal: <SIGNAL_NAME>", and an ERROR log entry is created with signal details
- **FR-003**: System MUST inject environment variables (SKILL_NAME, SKILL_BASE_DIR, SKILL_VERSION, SKILLKIT_VERSION) before script execution
- **FR-004**: System MUST validate script paths using FilePathResolver before execution to prevent path traversal attacks; script paths MAY contain spaces and special characters (all characters allowed except path separators .., /, \); validation focuses on ensuring the resolved path is within the skill base directory, not restricting filename characters
- **FR-005**: System MUST enforce execution timeouts with configurable duration (default 30 seconds) and kill processes that exceed the timeout
- **FR-006**: System MUST reject scripts with setuid or setgid permissions before execution
- **FR-007**: System MUST log all script executions with timestamp, skill name, script path, arguments (truncated to 256 chars), exit code, and execution time for security auditing
- **FR-008**: System MUST enforce tool restrictions by checking if "Bash" is in the skill's allowed-tools list before executing scripts
- **FR-009**: System MUST detect executable scripts lazily during skill invocation (after content is loaded but before script execution) by scanning skill directories for files with executable extensions (.py, .sh, .js, .rb, .pl); interpreter selection uses extension-based mapping (.py → python3, .sh → bash, .js → node, .rb → ruby, .pl → perl) with shebang line fallback for edge cases; description extraction MUST parse the first comment block (using #, //, or """ delimiters depending on script type) and use it as the script's description; if no comment block exists, description MUST be empty string
- **FR-010**: System MUST resolve symlinks and verify the final resolved path is within the skill base directory
- **FR-011**: System MUST pass arguments to scripts as JSON-serialized data via stdin (scripts read from standard input and parse JSON); this prevents shell interpolation and injection attacks while supporting complex data structures
- **FR-012**: System MUST handle script execution errors gracefully by returning error information in the execution result rather than crashing
- **FR-013**: Users MUST be able to configure script timeout via SkillManager initialization parameter
- **FR-014**: Users MUST be able to execute scripts directly via SkillManager.execute_skill_script() API; LangChain integration MUST create a separate StructuredTool for each detected script (e.g., skill "pdf-extractor" with scripts "extract.py", "convert.sh", "parse.py" generates three tools: "pdf-extractor.extract", "pdf-extractor.convert", "pdf-extractor.parse", each invoking its respective script); if the skill has a prompt, the prompt-based tool is preserved alongside script tools (skills can expose 1+N tools: one prompt tool + N script tools); script-based tools MUST declare a free-form JSON input schema (single field accepting any JSON structure) that passes agent-provided data directly to the script via stdin; on successful execution (exit_code==0), tools MUST return stdout as content with is_error=false; on failure (exit_code!=0), tools MUST raise exception with stderr as message and is_error=true; return format follows structure: {"type": "tool_result", "tool_use_id": "<id>", "content": "string | list | null", "is_error": boolean}
- **FR-015**: System MUST scan both `scripts/` directory (primary) and skill root directory (secondary fallback) for executable files
- **FR-016**: System MUST support nested script directories (e.g., `scripts/utils/parser.py`) up to reasonable depth
- **FR-017**: Script detection MUST complete in under 10ms for skills with fewer than 50 scripts
- **FR-018**: System MUST return execution results in a structured format (ScriptExecutionResult dataclass) with stdout, stderr, exit_code, execution_time_ms, and script_path fields
- **FR-019**: System MUST raise an InterpreterNotFoundError if the required interpreter (python3, bash, node, ruby, perl) is not available in PATH during script execution

### Key Entities *(include if feature involves data)*

- **ScriptExecutionResult**: Represents the outcome of a script execution with stdout (captured output), stderr (captured errors), exit_code (process exit status), execution_time_ms (duration in milliseconds), and script_path (relative path to executed script)
- **ScriptToolResult**: Represents the formatted return value from LangChain script tools with type ("tool_result"), tool_use_id (unique identifier), content (stdout string on success, null on error), and is_error (false for exit_code==0, true otherwise); exceptions are raised for failures with stderr as the error message
- **ScriptMetadata**: Represents detected script information with name (filename without extension), path (relative path from skill base directory), script_type (language/interpreter like python, bash, node), and description (string extracted from first comment block using #, //, or """ delimiters; empty string if no comment exists)
- **ScriptExecutor**: Component responsible for executing scripts with security controls, timeout enforcement, environment injection, and output capture
- **ScriptDetector**: Component responsible for scanning skill directories and identifying executable scripts based on extensions and shebang lines

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Scripts execute with less than 50ms overhead (excluding actual script runtime) for 95% of executions
- **SC-002**: 100% of path traversal attacks (tested with patterns like `../../etc/passwd`, `/etc/passwd`, symlinks outside skill dir) are blocked before execution
- **SC-003**: All script outputs up to 10MB are captured completely without truncation or data loss; outputs exceeding 10MB are truncated at the limit with a WARNING log entry including skill name, script path, and actual output size
- **SC-004**: Script timeouts are enforced within ±100ms of configured timeout value
- **SC-005**: 100% of script executions are logged with all required audit fields (timestamp, skill name, script path, exit code, duration)
- **SC-006**: Tool restriction enforcement prevents 100% of unauthorized script executions when Bash is not in allowed-tools
- **SC-007**: Script detection completes in under 10ms for 95% of skills with 50 or fewer scripts
- **SC-008**: Scripts execute successfully across all supported platforms (Linux, macOS, Windows) with consistent behavior
- **SC-009**: All script execution errors are handled gracefully with zero system crashes caused by script failures
- **SC-010**: Users can successfully configure custom timeouts ranging from 1 second to 600 seconds (10 minutes)

## Assumptions *(mandatory)*

- Scripts are provided by trusted skill authors; the system validates paths and permissions but doesn't sandbox script execution beyond OS-level permissions
- The agent process has necessary permissions to execute scripts; required interpreters (python3, bash, node, ruby, perl) are available in PATH and mapped from file extensions with shebang fallback
- Scripts read arguments as JSON from stdin and write results to stdout; they don't rely on shell-specific features that require `shell=True`
- Concurrent script executions are supported with independent subprocesses per invocation; scripts are responsible for managing their own file-level concurrency (e.g., file locking) if needed
- Performance targets assume modern hardware (SSD storage, multi-core CPU) and reasonable script complexity
- Audit logging uses Python's standard logging framework; persistence and log rotation are handled by deployment configuration
- Tool restriction enforcement is complementary to framework-level tool filtering; frameworks may provide additional controls
- Script detection runs once during skill invocation (lazy, not during initial discovery) to minimize performance impact
- Script outputs are captured up to 10MB per stream (stdout/stderr); outputs exceeding this limit are truncated with logged warnings; skills requiring larger outputs should write to files instead
- Resource limits (CPU, memory) are enforced at the OS/container level, not by skillkit library
- Cross-platform compatibility assumes standard interpreters (Python 3.10+, bash/sh, Node.js) are installed and available

## Dependencies & Constraints *(optional - include only if applicable)*

### Dependencies

- **FilePathResolver** (v0.2.0+): Required for path security validation and traversal prevention
- **SkillManager** (v0.2.0+): Required for skill lifecycle management and integration
- **SkillMetadata** (v0.1.0+): Required for accessing skill metadata (name, version, allowed-tools)
- **Python subprocess module** (stdlib): Required for process execution and output capture
- **Python pathlib module** (stdlib): Required for path manipulation and validation

### Constraints

- Script execution timeout maximum is 600 seconds (10 minutes) to prevent indefinite hangs
- Argument truncation in logs occurs at 256 characters to prevent log spam
- Script detection depth is limited to 5 levels of nesting to prevent excessive filesystem traversal
- Environment variable injection is limited to 4 core variables (SKILL_NAME, SKILL_BASE_DIR, SKILL_VERSION, SKILLKIT_VERSION) in v0.3.0
- Scripts execute with the same permissions as the agent process (no privilege escalation or sandboxing)
- Script detection caches results for the skill's lifetime in memory (no persistent caching across sessions)

## Out of Scope *(optional - include only if useful for clarity)*

- **Script result caching**: Caching of script execution results for identical inputs is deferred to v0.4.0
- **Resource limits enforcement**: CPU and memory limits for scripts are delegated to OS/container level, not enforced by skillkit
- **Advanced metadata extraction**: Parsing docstrings for argument schemas and return types is deferred to v0.4.0+
- **Script sandboxing**: Containerization or chroot environments for script isolation are deployment concerns, not library features
- **Network access control**: Blocking or monitoring script network requests is deferred to deployment layer
- **Script package management**: Installing script dependencies (pip install, npm install) is the skill author's responsibility
- **Script versioning**: Managing multiple versions of the same script is out of scope for v0.3.0
- **Binary executable support**: Only interpreted scripts (Python, Shell, JavaScript, etc.) are supported; compiled binaries are not validated or executed

## Related Work *(optional - include only if relevant)*

- **FR-5 (File Reference Resolution)**: Script execution leverages the same FilePathResolver infrastructure for path security
- **FR-4.3 (Tool Restrictions)**: Script execution integrates with tool restriction enforcement (requires "Bash" in allowed-tools)
- **v0.2.0 File Path Resolution**: Existing security patterns for validating file references are reused for script paths
- **Anthropic Skills Specification**: Script execution aligns with Anthropic's skill format, enabling 100% compatibility with Anthropic skills that include scripts
- **LangChain Integration**: Each detected script is exposed as a separate StructuredTool instance with naming pattern `{skill_name}.{script_name}` (e.g., "pdf-extractor" skill with "extract.py" and "convert.sh" generates "pdf-extractor.extract" and "pdf-extractor.convert" tools); skills with prompts retain their prompt-based tool (named `{skill_name}`) alongside script tools, allowing skills to expose both conversational guidance (via prompt) and deterministic operations (via scripts); script tool descriptions are extracted from the first comment block in each script file (empty string if no comment exists), with free-form JSON input schemas; tools return stdout on success (exit_code==0) or raise exception with stderr on failure (exit_code!=0), following format: {"type": "tool_result", "tool_use_id": "<id>", "content": "string | list | null", "is_error": boolean}; this maintains backward compatibility with v0.1/v0.2 while extending capabilities
