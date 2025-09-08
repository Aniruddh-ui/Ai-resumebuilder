document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("resumeForm");
  const outputDiv = document.getElementById("output");
  const userDescDiv = document.getElementById("userDescription");
  const downloadPdf = document.getElementById("downloadPdf");
  const downloadDocx = document.getElementById("downloadDocx");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const payload = {};

    formData.forEach((value, key) => {
      if (value.trim() !== "") {
        if (key === "skills" || key === "languages") {
          payload[key] = value.split(",").map(s => s.trim()).filter(Boolean);
        } else {
          payload[key] = value;
        }
      }
    });

    outputDiv.innerHTML = "<p>Generating resume, please wait...</p>";
    userDescDiv.style.display = "none";
    userDescDiv.innerHTML = "";
    downloadPdf.style.display = "none";
    downloadDocx.style.display = "none";
    downloadPdf.href = "#";
    downloadDocx.href = "#";

    try {
      const response = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        // Improved validation error message for FastAPI/Pydantic
        if (data.detail && Array.isArray(data.detail)) {
          outputDiv.innerHTML = `<p style="color:red;">Error:<br>` +
            data.detail.map(err => `${err.loc ? err.loc.join('.') : ''}: ${err.msg}`).join('<br>') +
            `</p>`;
        } else {
          outputDiv.innerHTML = `<p style="color:red;">Error: ${data.detail || data.error || response.statusText}</p>`;
        }
        return;
      }

      outputDiv.innerHTML = `<pre>${data.resume_text || ""}</pre>`;

      if (data.user_description) {
        userDescDiv.style.display = "block";
        userDescDiv.innerHTML = `<h3>User Description</h3><p>${data.user_description}</p>`;
      }

      downloadPdf.style.display = "inline-block";
      downloadDocx.style.display = "inline-block";
      downloadPdf.href = data.pdf_file || "/download/pdf";
      downloadDocx.href = data.docx_file || "/download/docx";
    } catch (err) {
      outputDiv.innerHTML = `<p style="color:red;">An error occurred: ${err.message}</p>`;
    }
  });
});
