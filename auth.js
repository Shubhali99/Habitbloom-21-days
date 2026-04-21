async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }

  return data;
}

async function getSession() {
  const data = await apiRequest("/api/session", { method: "GET" });
  return data.authenticated ? data.user : null;
}

async function updateTopbar() {
  const session = await getSession();
  const userWelcome = document.getElementById("userWelcome");
  const logoutButton = document.getElementById("logoutButton");

  if (userWelcome) {
    if (session) {
      userWelcome.hidden = false;
      userWelcome.textContent = `Hi, ${session.name}`;
    } else {
      userWelcome.hidden = true;
      userWelcome.textContent = "";
    }
  }

  if (logoutButton) {
    logoutButton.hidden = !session;
    logoutButton.onclick = async () => {
      await apiRequest("/api/logout", { method: "POST", body: JSON.stringify({}) });
      window.location.href = "login.html";
    };
  }

  document.querySelectorAll(".text-link").forEach((link) => {
    const href = link.getAttribute("href");
    if (!href) {
      return;
    }

    if (session && (href === "login.html" || href === "signup.html")) {
      link.hidden = true;
    }
  });
}

async function requireSessionForTracker() {
  if (!document.getElementById("daysGrid")) {
    return;
  }

  const session = await getSession();
  const authMessage = document.getElementById("authMessage");

  if (!session) {
    window.location.href = "login.html";
    return;
  }

  if (authMessage) {
    authMessage.textContent = `Logged in as ${session.email}`;
  }
}

function handleSignupPage() {
  const signupForm = document.getElementById("signupForm");
  if (!signupForm) {
    return;
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(signupForm);
    const name = String(formData.get("name") || "").trim();
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    const feedback = document.getElementById("signupFeedback");

    if (!name || !email || password.length < 8) {
      feedback.textContent = "Enter your name, email, and a password with at least 8 characters.";
      feedback.dataset.state = "error";
      return;
    }

    try {
      feedback.textContent = "Creating your account...";
      feedback.dataset.state = "";
      await apiRequest("/api/signup", {
        method: "POST",
        body: JSON.stringify({ name, email, password })
      });
      window.location.href = "index.html";
    } catch (error) {
      feedback.textContent = error.message;
      feedback.dataset.state = "error";
    }
  });
}

function handleLoginPage() {
  const loginForm = document.getElementById("loginForm");
  if (!loginForm) {
    return;
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(loginForm);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    const feedback = document.getElementById("loginFeedback");

    try {
      feedback.textContent = "Signing you in...";
      feedback.dataset.state = "";
      await apiRequest("/api/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      window.location.href = "index.html";
    } catch (error) {
      feedback.textContent = error.message;
      feedback.dataset.state = "error";
    }
  });
}

async function protectAuthPages() {
  const isAuthPage = document.getElementById("loginForm") || document.getElementById("signupForm");
  if (!isAuthPage) {
    return;
  }

  try {
    const session = await getSession();
    if (session) {
      window.location.href = "index.html";
    }
  } catch (error) {
    // Leave the auth page accessible if the server is unavailable.
  }
}

window.habitTrackerAuth = {
  apiRequest,
  getSession
};

updateTopbar();
requireSessionForTracker();
handleSignupPage();
handleLoginPage();
protectAuthPages();
