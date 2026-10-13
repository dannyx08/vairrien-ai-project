
document.addEventListener("DOMContentLoaded", () => {
    const client = supabaseClient;

    if (!client) {
        console.error("Supabase client was not initialized.");
        showMessage(
            "Authentication is temporarily unavailable. Please refresh the page.",
            true
        );
        return;
    }

    const signupForm = document.querySelector(
        "#signupForm, #signup-form"
    );

    const loginForm = document.querySelector("#loginForm");

    const googleButtons = document.querySelectorAll(
        "#googleSignup, #google-signup, .auth-google-button, .auth-google-button.auth-social-button, #google-login, .auth-social-button"
    );

    const messageElement =
        document.querySelector("#auth-message") ||
        document.querySelector("#authMessage");

    function showMessage(message, isError = false) {
        let target = messageElement;

        if (!target) {
            target = document.createElement("p");
            target.id = "auth-message";
            target.setAttribute("role", "status");
            target.setAttribute("aria-live", "polite");

            const form = signupForm || loginForm;

            if (form) {
                form.insertAdjacentElement("afterend", target);
            } else {
                return;
            }
        }

        target.textContent = message;
        target.style.marginTop = "16px";
        target.style.fontSize = "14px";
        target.style.lineHeight = "1.6";
        target.style.color = isError ? "#f0a09a" : "#c4d2ca";
    }

    function setLoading(button, loading, originalText) {
        if (!button) return;

        button.disabled = loading;
        button.style.opacity = loading ? "0.7" : "1";
        button.style.cursor = loading ? "wait" : "pointer";

        if (loading) {
            button.dataset.originalText = button.textContent.trim();
            button.textContent = "Please wait...";
        } else {
            button.textContent =
                button.dataset.originalText || originalText;
        }
    }

    // SIGN UP
    if (signupForm) {
        signupForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const nameInput =
                document.querySelector("#signupName") ||
                document.querySelector("#full-name");

            const emailInput =
                document.querySelector("#signupEmail") ||
                document.querySelector("#email");

            const passwordInput =
                document.querySelector("#signupPassword") ||
                document.querySelector("#password");

            const confirmInput =
                document.querySelector("#confirm-password");

            const termsInput = document.querySelector("#terms");

            const submitButton = signupForm.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            const name = nameInput?.value.trim() || "";
            const email = emailInput?.value.trim() || "";
            const password = passwordInput?.value || "";
            const confirmPassword = confirmInput?.value;
            
            if (!name) {
                showMessage("Please enter your full name.", true);
                return;
            }

            if (!email) {
                showMessage("Please enter your email address.", true);
                return;
            }

            if (password.length < 8) {
                showMessage(
                    "Your password must contain at least 8 characters.",
                    true
                );
                return;
            }

            if (
                confirmPassword !== undefined &&
                password !== confirmPassword
            ) {
                showMessage("Your passwords do not match.", true);
                return;
            }

            if (termsInput && !termsInput.checked) {
                showMessage(
                    "Please accept the Terms and Privacy Policy to continue.",
                    true
                );
                return;
            }

            setLoading(submitButton, true, "Create account");
            showMessage("Creating your account...");

            try {
                const { data, error } = await client.auth.signUp({
                    email,
                    password,
                    options: {
                        data: {
                            full_name: name,
                            name: name
                        },
                        emailRedirectTo:
                            `${window.location.origin}/dashboard.html`
                    }
                });

                if (error) throw error;

                if (data.session) {
                    window.location.assign("dashboard.html");
                    return;
                }

                showMessage(
                    "Your account has been created. Check your email to confirm your address, then log in."
                );

                signupForm.reset();
            } catch (error) {
                console.error("Signup error:", error);
                showMessage(
                    error.message || "Unable to create your account.",
                    true
                );
            } finally {
                setLoading(submitButton, false, "Create account");
            }
        });
    }

    // LOG IN
    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const emailInput = document.querySelector("#loginEmail");
            const passwordInput = document.querySelector("#loginPassword");
            const submitButton = loginForm.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            const email = emailInput?.value.trim() || "";
            const password = passwordInput?.value || "";

            if (!email || !password) {
                showMessage(
                    "Enter your email address and password.",
                    true
                );
                return;
            }

            setLoading(submitButton, true, "Log in");
            showMessage("Signing you in...");

            try {
                const { data, error } =
                    await client.auth.signInWithPassword({
                        email,
                        password
                    });

                if (error) throw error;

                if (!data.session) {
                    showMessage(
                        "No active session was created. Please try again.",
                        true
                    );
                    return;
                }

                window.location.assign("dashboard.html");
            } catch (error) {
                console.error("Login error:", error);
                showMessage(
                    error.message ||
                    "Unable to log in. Check your details and try again.",
                    true
                );
            } finally {
                setLoading(submitButton, false, "Log in");
            }
        });
    }

    // GOOGLE SIGN-IN
    googleButtons.forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();

            button.disabled = true;
            showMessage("Connecting to Google...");

            try {
                const { error } = await client.auth.signInWithOAuth({
                    provider: "google",
                    options: {
                        redirectTo:
                            `${window.location.origin}/dashboard.html`
                    }
                });

                if (error) throw error;
            } catch (error) {
                console.error("Google sign-in error:", error);
                button.disabled = false;

                showMessage(
                    error.message ||
                    "Google sign-in could not be started.",
                    true
                );
            }
        });
    });

    // FORGOT PASSWORD
    const forgotPasswordLink = [...document.querySelectorAll("a")]
        .find((link) =>
            link.textContent.trim().toLowerCase() === "forgot password?"
        );

    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener("click", async (event) => {
            event.preventDefault();

            const emailInput = document.querySelector("#loginEmail");
            const email = emailInput?.value.trim() || "";

            if (!email) {
                showMessage(
                    "Enter your email address first, then select Forgot password.",
                    true
                );
                emailInput?.focus();
                return;
            }

            try {
                const { error } = await client.auth.resetPasswordForEmail(
                    email,
                    {
                        redirectTo:
                            `${window.location.origin}/login.html`
                    }
                );

                if (error) throw error;

                showMessage(
                    "If password recovery is available for this account, check your inbox for the recovery email."
                );
            } catch (error) {
                console.error("Password reset error:", error);
                showMessage(
                    error.message || "Unable to request a password reset.",
                    true
                );
            }
        });
    }
});