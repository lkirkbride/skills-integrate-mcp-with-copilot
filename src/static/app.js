document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const guestControls = document.getElementById("guest-controls");
  const sessionControls = document.getElementById("session-controls");
  const sessionEmail = document.getElementById("session-email");
  const studentContainer = document.getElementById("student-container");
  const registrationsList = document.getElementById("registrations-list");
  const changePasswordForm = document.getElementById("change-password-form");
  let authenticated = false;

  function showMessage(message, type = "success", persistent = false) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    if (!persistent) {
      setTimeout(() => messageDiv.classList.add("hidden"), 5000);
    }
  }

  async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "An unexpected error occurred");
    }
    return result;
  }

  function jsonOptions(method, body) {
    return {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    };
  }

  function setAuthenticatedState(session) {
    authenticated = session.authenticated;
    guestControls.classList.toggle("hidden", authenticated);
    sessionControls.classList.toggle("hidden", !authenticated);
    studentContainer.classList.toggle("hidden", !authenticated);
    changePasswordForm.classList.toggle("hidden", !authenticated);
    sessionEmail.textContent = session.email || "";
  }

  async function fetchSession() {
    const session = await apiRequest("/session");
    setAuthenticatedState(session);
    if (session.authenticated) {
      await fetchDashboard();
    }
  }

  async function fetchActivities() {
    try {
      const activities = await apiRequest("/activities");
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      Object.entries(activities).forEach(([name, details]) => {
        const spotsLeft = details.max_participants - details.participant_count;
        const activityCard = document.createElement("article");
        activityCard.className = "activity-card";

        const heading = document.createElement("h4");
        heading.textContent = name;
        const description = document.createElement("p");
        description.textContent = details.description;
        const schedule = document.createElement("p");
        schedule.innerHTML = "<strong>Schedule:</strong> ";
        schedule.append(details.schedule);
        const availability = document.createElement("p");
        availability.innerHTML = "<strong>Availability:</strong> ";
        availability.append(`${spotsLeft} spots left`);

        activityCard.append(heading, description, schedule, availability);
        activitiesList.appendChild(activityCard);
        activitySelect.add(new Option(name, name));
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function fetchDashboard() {
    try {
      const dashboard = await apiRequest("/me");
      registrationsList.innerHTML = "";
      if (dashboard.registrations.length === 0) {
        registrationsList.innerHTML = "<p><em>You have not joined any activities yet.</em></p>";
        return;
      }

      dashboard.registrations.forEach((registration) => {
        const card = document.createElement("article");
        card.className = "registration-card";
        const heading = document.createElement("h4");
        heading.textContent = registration.name;
        const schedule = document.createElement("p");
        schedule.textContent = registration.schedule;
        const cancelButton = document.createElement("button");
        cancelButton.type = "button";
        cancelButton.className = "danger";
        cancelButton.textContent = "Cancel Registration";
        cancelButton.addEventListener("click", () => cancelRegistration(registration.name));
        card.append(heading, schedule, cancelButton);
        registrationsList.appendChild(card);
      });
    } catch (error) {
      if (authenticated) {
        showMessage(error.message, "error");
      }
    }
  }

  async function refreshStudentData() {
    await Promise.all([fetchActivities(), fetchDashboard()]);
  }

  async function cancelRegistration(activity) {
    try {
      const result = await apiRequest(
        `/activities/${encodeURIComponent(activity)}/unregister`,
        { method: "DELETE" }
      );
      showMessage(result.message);
      await refreshStudentData();
    } catch (error) {
      showMessage(error.message, "error");
    }
  }

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".account-form").forEach((form) => form.classList.add("hidden"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.form).classList.remove("hidden");
    });
  });

  document.getElementById("register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await apiRequest(
        "/accounts",
        jsonOptions("POST", {
          email: document.getElementById("register-email").value,
          password: document.getElementById("register-password").value,
        })
      );
      showMessage(
        `${result.message} Recovery code: ${result.recovery_code}`,
        "info",
        true
      );
      event.target.reset();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await apiRequest(
        "/sessions",
        jsonOptions("POST", {
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value,
        })
      );
      event.target.reset();
      showMessage(result.message);
      await fetchSession();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  document.getElementById("reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await apiRequest(
        "/accounts/password-reset",
        jsonOptions("POST", {
          email: document.getElementById("reset-email").value,
          recovery_code: document.getElementById("recovery-code").value,
          new_password: document.getElementById("reset-password").value,
        })
      );
      event.target.reset();
      showMessage(
        `${result.message} Recovery code: ${result.recovery_code}`,
        "info",
        true
      );
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  changePasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const result = await apiRequest(
        "/accounts/password",
        jsonOptions("PUT", {
          current_password: document.getElementById("current-password").value,
          new_password: document.getElementById("new-password").value,
        })
      );
      event.target.reset();
      showMessage(result.message);
      await fetchSession();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  document.getElementById("logout-button").addEventListener("click", async () => {
    try {
      const result = await apiRequest("/sessions/current", { method: "DELETE" });
      showMessage(result.message);
      await fetchSession();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const activity = activitySelect.value;
      const result = await apiRequest(
        `/activities/${encodeURIComponent(activity)}/signup`,
        { method: "POST" }
      );
      signupForm.reset();
      showMessage(result.message);
      await refreshStudentData();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  Promise.all([fetchActivities(), fetchSession()]).catch((error) => {
    showMessage(error.message, "error");
  });
});
