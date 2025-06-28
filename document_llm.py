import requests

file_path = "sec-edgar-filings/documents/document_1_converted.html"  # Replace with your actual file name

# with open(file_path, "r", encoding="utf-8") as f:
#     text = f.read()
# approx_tokens = len(text) // 4
#
# print(f"Estimated token count: {approx_tokens}")


def send_to_gemma(chunk, prompt_suffix="Please summarize this chunk:"):
    prompt = f"{chunk}\n\n{prompt_suffix}"
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma:7b",
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 8192},
        },
    )
    result = response.json().get("response", "")
    # Check if teh phrase provided text does not contain any information
    if (
        "does not contain any information" in result.lower()
        or "provided text does not include" in result.lower()
    ):
        return ""
    return response.json().get("response", "")


def send_to_gemma_yes_or_no(chunk, question):
    prompt = (
        f"Text:\n{chunk}\n\n"
        f"Question: {question}\n"
        "Answer with only 'Yes' or 'No' (no explanation):"
    )
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma:7b", "prompt": prompt, "stream": False},
    )
    answer = response.json().get("response", "").strip()
    # Clean response to just yes/no
    if answer.lower().startswith("yes"):
        return "Yes"
    elif answer.lower().startswith("no"):
        return "No"
    else:
        # fallback or uncertain
        return answer


def chunk_text(text, max_tokens=6000, overlap_tokens=200):
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)

        # Move start forward, but keep overlap with previous chunk
        start = end - overlap_chars
        if start < 0:
            start = 0

    return chunks


# Load your large document
with open(file_path, "r") as f:
    document = f.read()

# Chunk the document
chunks = chunk_text(document)

# Process chunks one by one and collect summaries
summaries = []
for i, chunk in enumerate(chunks):
    print(f"Processing chunk {i + 1}/{len(chunks)}")
    #
    answer = send_to_gemma_yes_or_no(
        chunk, question="Does this chunk refer to who the subject of this document is?"
    )
    if answer == "Yes":
        summary = send_to_gemma(
            chunk,
            prompt_suffix="Tell me what this chunk has to say about who is the subject of the document.",
        )
        # print("Summary:", summary)
        summaries.append(summary)


print(summaries)
print(len(summaries))
summaries = set(summaries)
print(summaries)
print(len(summaries))
combined_summary = "\n".join(summaries)
# print("Combined summary:\n", combined_summary)
final_statement = send_to_gemma(
    combined_summary,
    prompt_suffix="Who is the subject of the document",
)
print(final_statement)
