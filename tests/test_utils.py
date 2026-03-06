import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.utils import (
    parse_resume, 
    generate_embeddings, 
    save_resume_embedding,
    load_resume_embedding,
    chunk_resume,
    save_resume_chunks,
    load_resume_chunks,
    compute_similarity,
    get_company_links
)
import numpy as np
print("=== Test1: Retrieve config ===")
links = get_company_links()
print(f"Company links: {links}")

print("\n=== Test2: Parse resume ===")
resume_text = parse_resume(file_path="data/resumes/Kerui Liu Resume - sde - Agentic AI.pdf")
print(f"Resume text length: {len(resume_text)} characters")
print(f"First 200 chars: {resume_text[:200]}")
print(f"All chars: {resume_text}")


print("\n=== Test3: Generate whole resume embedding ===")
resume_embeddings = generate_embeddings([resume_text])
print(f"Embedding shape (2D): {resume_embeddings.shape}")
# Extract single embedding from batch
resume_embedding = resume_embeddings[0]  # Get first (and only) embedding
print(f"Single embedding shape (1D): {resume_embedding.shape}")
print(f"Embedding norm: {np.linalg.norm(resume_embedding):.4f}")  # 应该接近1

print("\n=== Test4: Save resume embedding ===")
save_resume_embedding(resume_embedding)  # Save 1D array

print("\n=== Test5: Load resume embedding ===")
loaded_resume_embedding = load_resume_embedding()
print(f"Loaded embedding shape: {loaded_resume_embedding.shape}")
print(f"Embeddings match: {np.allclose(resume_embedding, loaded_resume_embedding)}")

print("\n=== Test6: Chunk resume ===")
chunks = chunk_resume(resume_text)
print(f"Number of chunks: {len(chunks)}")
for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
    print(f"\nChunk {i+1} ({len(chunk)} chars):")
    print(f"  {chunk[:100]}...")

print("\n=== Test7: Generate chunk embeddings ===")
chunk_embeddings = generate_embeddings(chunks)
print(f"Chunk embeddings shape: {chunk_embeddings.shape}")
print(f"Expected: ({len(chunks)}, 768)")

print("\n=== Test8: Save resume chunks ===")
save_resume_chunks(chunks, chunk_embeddings)
print("✓ Saved resume chunks and embeddings")

print("\n=== Test9: Load resume chunks ===")
loaded_chunks, loaded_embeddings = load_resume_chunks()
print(f"Loaded {len(loaded_chunks)} chunks")
print(f"Embeddings shape: {loaded_embeddings.shape}")
print(f"Chunks match: {loaded_chunks == chunks}")
print(f"Embeddings match: {np.allclose(chunk_embeddings, loaded_embeddings)}")

print("\n=== Test10: Compute Similarity ===")
# Self similarity (should be close to 1.0)
similarity = compute_similarity(loaded_resume_embedding, resume_embedding)
print(f"Self similarity: {similarity:.4f}")  # should close to 1.0

# Compare with a job description
job_text = "We are looking for a software engineer with Python experience"
job_embedding = generate_embeddings([job_text])[0]  # Extract single embedding
similarity2 = compute_similarity(resume_embedding, job_embedding)
print(f"Resume vs job similarity: {similarity2:.4f}")

print("\n=== Tests all done! ===")