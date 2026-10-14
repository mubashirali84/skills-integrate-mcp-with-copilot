document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const teacherLoginButton = document.getElementById("teacher-login-button");
  const teacherLogoutButton = document.getElementById("teacher-logout-button");
  const teacherStatus = document.getElementById("teacher-status");
  const teacherSigninPrompt = document.getElementById("teacher-signin-prompt");
  const teacherLoginDialog = document.getElementById("teacher-login-dialog");
  const teacherLoginForm = document.getElementById("teacher-login-form");
  const teacherLoginMessage = document.getElementById("teacher-login-message");
  let isTeacher = false;

  function setTeacherMode(authenticated, username = "") {
    isTeacher = authenticated;
    teacherLoginButton.classList.toggle("hidden", authenticated);
    teacherLogoutButton.classList.toggle("hidden", !authenticated);
    teacherStatus.classList.toggle("hidden", !authenticated);
    teacherStatus.textContent = authenticated ? `Signed in as ${username}` : "";
    signupForm.classList.toggle("hidden", !authenticated);
    teacherSigninPrompt.classList.toggle("hidden", authenticated);
  }

  function showMessage(element, text, status) {
    element.textContent = text;
    element.className = status;
    setTimeout(() => element.classList.add("hidden"), 5000);
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error(`Activity request failed with status ${response.status}`);
      }
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${escapeHTML(email)}</span>${
                        isTeacher
                          ? `<button class="delete-btn" data-activity="${escapeHTML(name)}" data-email="${escapeHTML(email)}" type="button" aria-label="Remove ${escapeHTML(email)} from ${escapeHTML(name)}">Remove</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${escapeHTML(name)}</h4>
          <p>${escapeHTML(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHTML(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);
        activitySelect.add(new Option(name, name));
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function refreshSession() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) {
        throw new Error(`Session request failed with status ${response.status}`);
      }
      const session = await response.json();
      setTeacherMode(session.authenticated, session.username || "");
    } catch (error) {
      setTeacherMode(false);
      console.error("Error checking teacher session:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        await fetchActivities();
      } else {
        if (response.status === 401) setTeacherMode(false);
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(messageDiv, "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = activitySelect.value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        { method: "POST" }
      );
      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        if (response.status === 401) setTeacherMode(false);
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(messageDiv, "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  teacherLoginButton.addEventListener("click", () => {
    teacherLoginMessage.classList.add("hidden");
    teacherLoginDialog.showModal();
    document.getElementById("teacher-username").focus();
  });

  document
    .getElementById("teacher-login-cancel")
    .addEventListener("click", () => teacherLoginDialog.close());

  teacherLoginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(teacherLoginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        showMessage(
          teacherLoginMessage,
          result.detail || "Unable to sign in.",
          "error"
        );
        return;
      }

      setTeacherMode(true, result.username);
      teacherLoginForm.reset();
      teacherLoginDialog.close();
      await fetchActivities();
    } catch (error) {
      showMessage(
        teacherLoginMessage,
        "Unable to sign in. Please try again.",
        "error"
      );
      console.error("Error signing in:", error);
    }
  });

  teacherLogoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error(`Sign-out request failed with status ${response.status}`);
      }
      setTeacherMode(false);
      await fetchActivities();
      showMessage(messageDiv, "Signed out successfully.", "success");
    } catch (error) {
      showMessage(messageDiv, "Unable to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  refreshSession().then(fetchActivities);
});
