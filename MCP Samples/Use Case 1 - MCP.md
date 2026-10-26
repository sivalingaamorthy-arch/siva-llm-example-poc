# Use Case 1 — MCP hands-on example

This use case introduces the **Model Context Protocol (MCP)** by exposing a
small well-being demo and the retrieval flow from Use Case 1 — RAG as MCP
capabilities. It explains what each lab demonstrates and why the concept is
useful; the runnable code is in this folder.

This is a learning example, not a production or clinical service. Use only the
bundled synthetic reports. Never submit real health or personal data.

> **Run the example:** follow [NOTES.md](./NOTES.md) for setup and commands.
> The [project README](./README.md) describes the implemented tools and their
> requirements.

## What you will learn

MCP standardizes how an AI application can discover and use capabilities
provided by another process or service. The example follows a request from the
**host** (the AI application), through its **MCP client**, to the **MCP
server**. The server exposes a few capabilities from this project and, for the
retrieval lab, calls the existing RAG implementation rather than reimplementing
search.

The labs progress from a small tool to integration, then explore how the
protocol's primitives, transports, state, and security boundaries fit
together. Labs 1–3 are the shortest path to the main result; later labs build
understanding and include design exercises rather than deployed infrastructure.

## Lab map

| Lab | Example | Why it matters |
|---|---|---|
| 0 | Set up the Python project | A repeatable environment makes the example easier to run and inspect. |
| 1 | Inspect and call a tool | Learn how tool descriptions and input types become a discoverable schema. |
| 2 | Connect a host over stdio | See that the host owns the client and mediates tool calls and consent. |
| 3 | Expose RAG recommendations | See how MCP can adapt an existing domain capability without accepting arbitrary health data. |
| 4 | Read a resource and render a prompt | Compare who chooses tools, resources, and prompts. |
| 5 | Call the server over HTTP | Compare local process transport with a network transport and inspect protocol messages. |
| 6 | Carry state using a handle | See why explicit resource identifiers work better than hidden connection state. |
| 7 | Design a gateway policy | Understand where authentication, authorization, routing, and audit belong. |
| 8 | Test destructive-tool protection | See why host approval and descriptive annotations do not replace server authorization. |

## Labs

### Lab 0 — Prepare the project

Use `uv` to install the dependencies declared by this project, then confirm
the installed MCP SDK version. The lockfile makes the environment reproducible.
The article catalog, sample reports, and evaluation references are shared from
[`../Sample-Data-Health-Content/`](../Sample-Data-Health-Content/README.md).
The [run notes](./NOTES.md) give the exact commands.

The MCP project is separate from the RAG application. Labs 1, 2, 4, and the
basic HTTP example do not need the RAG database or an OpenAI key. Lab 3 uses
the sibling `RAG Samples/` retrieval implementation, PostgreSQL with pgvector,
seeded article embeddings, and an OpenAI API key.

**Why:** separating setup from the individual experiments makes it clearer
which dependencies belong to MCP and which belong to retrieval.

### Lab 1 — Inspect a tool and its schema

Open the server in the MCP Inspector and list its tools. Start with `bmi`:
call it with `72` kg and `1.75` m, then try an invalid value such as a height
of zero. Inspect the generated input schema and the error result.

The schema comes from the function's type hints; the function description tells
the host what the tool is for. The server validates the values and returns an
error for invalid input rather than terminating.

**Why:** an AI model chooses tools based on the names, descriptions, and schemas
it can see. Those descriptions are part of the API contract, not decoration.

### Lab 2 — Connect a host over stdio

Register the server with Claude Code using the command in [NOTES.md](./NOTES.md),
then confirm that it appears in the host's MCP server list and ask for a BMI
calculation.

Claude Code is the **host**: it starts the server process, owns the client
connection, makes the available tools visible to the model, and applies its
own approval policy. The model does not connect directly to the server. Whether
an approval prompt appears depends on the host's configuration.

**Why:** the protocol carries requests, but the host controls which servers and
tools the model may use and what the user must approve.

### Lab 3 — Expose the existing RAG retrieval

Call `recommendations_for_demo_report` with one of the fixed IDs: `R1`, `R2`,
or `R3`. The tool loads that bundled synthetic report, validates it, derives
the report markers, and calls the existing RAG retrieval function. Its result
is a bounded list of article IDs, titles, categories, tags, and similarity
scores—not full article bodies or generated medical advice.

The tool does not accept report contents or arbitrary report paths. Retrieval
requires the RAG database to be running and populated, plus OpenAI access for
embeddings. The report notes are sent to the configured OpenAI API as part of
the embedding request. Similarity is not a probability, a safety rating, or a
guarantee of relevance.

**Why:** MCP is an integration layer around an existing capability. Keeping
the input bounded and the output concise makes the tool easier to understand
and reduces the data exposed to the model.

**Try this:** compare the three fixtures. Then consider what would change if
the tool returned complete article bodies or if there were a separate tool for
every tag. Record the trade-off in output size and tool choice.

### Lab 4 — Compare tools, resources, and prompts

Use the `article://{article_id}` resource to read a bundled article. Render the
`recommend_for_profile` prompt with one of its supported age bands and goals.
Compare those actions with calling a tool.

- A **tool** is an action the model can choose to call.
- A **resource** is data the application or user chooses to load.
- A **prompt** is a reusable instruction the user chooses to invoke.

**Why:** these primitives have different control models. Choose between them
based on who should decide when information is loaded or an action is taken.
Treat article text as untrusted content, not as instructions.

### Lab 5 — Use Streamable HTTP

Start the server with the Streamable HTTP transport and call it using the
project's small MCP client. Inspect the tool result and, if desired, use the
Inspector to observe the exchange.

Stdio is convenient when the host launches a local server process. HTTP allows
a client to reach a server over a network. Both carry MCP messages; transport
does not change what a tool is allowed to do.

Protocol and SDK wire details can change. Prefer the exchange produced by the
installed SDK and compare it with the official transport specification rather
than relying on a copied request from an older tutorial. A successful BMI call
shows the tool working over HTTP; it does not by itself prove that every
deployment is stateless.

**Why:** knowing the transport boundary helps distinguish connection and
deployment concerns from the tool's behavior.

### Lab 6 — Keep workflow state behind an explicit handle

Use `start_shortlist` to create a shortlist, then pass the returned ID to
`add_to_shortlist` and `get_shortlist`. By default the example stores shortlists
in memory. Restarting the server loses that state. Set
`SHORTLIST_STORAGE=postgres` to use the shared PostgreSQL store instead.

The code creates its own shortlist tables; it does not change the RAG article
tables. The handle identifies the shortlist explicitly, rather than relying on
an MCP connection to remember which workflow is in progress.

**Why:** clients can pass a resource handle from call to call, and a shared
store can preserve state across server restarts or instances. The included
server command uses one default HTTP port; running multiple server instances
side by side requires additional server configuration.

### Lab 7 — Design the gateway boundary

This is a design exercise; the sample does not deploy an API gateway. Sketch a
host, a gateway, and one MCP server for each domain. Write a policy that
authenticates consumers, authorizes each tool per consumer, rate-limits calls,
and audits the **validated** tool name.

Routing headers supplied by a caller can help a gateway route a request, but
they are not proof of identity or permission. The server and gateway must
validate the request consistently. Remote authentication and OAuth also need
to be designed before exposing a server outside a trusted local environment.

**Why:** MCP adds a consumer-facing contract; it does not replace domain APIs or
remove the need for normal API governance.

### Lab 8 — Test security boundaries

The sample marks `clear_shortlist` as destructive so a host can display that
metadata. The server independently checks the operator-configured
`SHORTLIST_CLEAR_ALLOWED_IDS` allowlist before deleting anything. Try a
non-allowlisted ID and confirm that the call fails without changing the
shortlist. Only test an allowlisted ID in an isolated demo.

Then consider a synthetic article containing instructions that conflict with
the user's request. Tool results and article text are untrusted input. Record
how the host handles the content and whether it asks for approval before a
destructive action.

**Why:** annotations describe a tool; they do not enforce consent or
authorization. The host's approval policy and the server's authorization
checks solve different parts of the security problem.

## What to record

For each lab, write down what you tried, what you observed, and what the
observation demonstrates. Use the checklist and evidence log in
[NOTES.md](./NOTES.md). A test passing is useful evidence about the code, but
does not prove a live Claude Code interaction, a PostgreSQL deployment, or a
gateway policy.

## Limits and sources

This sample is educational software, not a medical or clinical system. Its
fixed filters do not establish that an article is suitable for an individual.
Use only the bundled synthetic reports, and do not commit secrets.

Check current SDK and protocol documentation before copying version-specific
examples:

- [MCP specification](https://modelcontextprotocol.io/specification/latest)
- [Streamable HTTP transport](https://modelcontextprotocol.io/specification/latest/basic/transports/streamable-http)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) and [SDK documentation](https://py.sdk.modelcontextprotocol.io/)
