/* ============================================================
   VAIRRIEN AI
   Landing Page JavaScript
============================================================ */

document.addEventListener("DOMContentLoaded", () => {

    /* ========================================================
       MOBILE NAVIGATION
    ========================================================= */

    const navbar = document.querySelector(".navbar");
    const mobileMenuButton = document.querySelector(".mobile-menu-button");
    const navigationLinks = document.querySelectorAll(".desktop-nav a");

    if (navbar && mobileMenuButton) {

        mobileMenuButton.addEventListener("click", () => {

            const isOpen = navbar.classList.toggle("menu-open");

            mobileMenuButton.setAttribute(
                "aria-expanded",
                String(isOpen)
            );

        });


        navigationLinks.forEach((link) => {

            link.addEventListener("click", () => {

                navbar.classList.remove("menu-open");

                mobileMenuButton.setAttribute(
                    "aria-expanded",
                    "false"
                );

            });

        });

    }


    /* ========================================================
       SMOOTH ANCHOR NAVIGATION
    ========================================================= */

    const anchorLinks = document.querySelectorAll(
        'a[href^="#"]'
    );

    anchorLinks.forEach((link) => {

        link.addEventListener("click", (event) => {

            const targetId = link.getAttribute("href");

            if (!targetId || targetId === "#") {
                return;
            }

            const target = document.querySelector(targetId);

            if (!target) {
                return;
            }

            event.preventDefault();

            const navbarHeight = navbar
                ? navbar.offsetHeight
                : 0;

            const targetPosition =
                target.getBoundingClientRect().top +
                window.scrollY -
                navbarHeight -
                15;

            window.scrollTo({
                top: targetPosition,
                behavior: "smooth"
            });

        });

    });


    /* ========================================================
       SHOWCASE OPTION INTERACTION
    ========================================================= */

    const showcaseButtons = document.querySelectorAll(
        ".showcase-options button"
    );

    const showcaseInput = document.querySelector(
        ".showcase-input span"
    );

    showcaseButtons.forEach((button) => {

        button.addEventListener("click", () => {

            const action = button.textContent.trim();

            if (showcaseInput) {

                showcaseInput.textContent =
                    `${action} with Vairrien...`;

            }

            showcaseButtons.forEach((item) => {
                item.classList.remove("selected");
            });

            button.classList.add("selected");

        });

    });


    /* ========================================================
       SIMPLE REVEAL ANIMATION
    ========================================================= */

    const revealElements = document.querySelectorAll(
        ".feature-card, .workflow-step, .resource-card"
    );


    if ("IntersectionObserver" in window) {

        const observer = new IntersectionObserver(
            (entries, observerInstance) => {

                entries.forEach((entry) => {

                    if (!entry.isIntersecting) {
                        return;
                    }

                    entry.target.classList.add("visible");

                    observerInstance.unobserve(entry.target);

                });

            },
            {
                threshold: 0.12
            }
        );


        revealElements.forEach((element) => {

            element.classList.add("reveal");

            observer.observe(element);

        });

    } else {

        revealElements.forEach((element) => {
            element.classList.add("visible");
        });

    }


    /* ========================================================
       NAVBAR SCROLL STATE
    ========================================================= */

    let lastScrollPosition = 0;

    window.addEventListener(
        "scroll",
        () => {

            const currentScrollPosition = window.scrollY;

            if (currentScrollPosition > 30) {
                navbar?.classList.add("scrolled");
            } else {
                navbar?.classList.remove("scrolled");
            }

            lastScrollPosition = currentScrollPosition;

        },
        {
            passive: true
        }
    );

});


/* =========================================================
   VAIRRIEN PLATFORM PAGE
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    const platformPage = document.querySelector(".platform-page");

    if (!platformPage) {
        return;
    }


    /* =====================================================
       PLATFORM INTERFACE NAVIGATION
    ====================================================== */

    const interfaceItems = document.querySelectorAll(
        ".interface-nav-item"
    );

    interfaceItems.forEach((item) => {

        item.addEventListener("click", () => {

            interfaceItems.forEach((navItem) => {
                navItem.classList.remove("active");
            });

            item.classList.add("active");

        });

    });


    /* =====================================================
       AI INPUT DEMO
    ====================================================== */

    const aiButton = document.querySelector(
        ".interface-ai-input button"
    );

    const aiInput = document.querySelector(
        ".interface-ai-input"
    );

    if (aiButton && aiInput) {

        aiButton.addEventListener("click", () => {

            aiInput.classList.add("is-processing");

            aiButton.textContent = "•";

            setTimeout(() => {

                aiInput.classList.remove("is-processing");

                aiButton.textContent = "✓";

            }, 900);

        });

    }


    /* =====================================================
       SCROLL REVEAL
    ====================================================== */

    const revealElements = document.querySelectorAll(
        ".platform-pillar, " +
        ".platform-feature, " +
        ".system-card, " +
        ".timeline-step, " +
        ".platform-cta-box"
    );

    if ("IntersectionObserver" in window) {

        const revealObserver = new IntersectionObserver(
            (entries, observer) => {

                entries.forEach((entry) => {

                    if (!entry.isIntersecting) {
                        return;
                    }

                    entry.target.classList.add(
                        "platform-visible"
                    );

                    observer.unobserve(entry.target);

                });

            },
            {
                threshold: 0.12
            }
        );

        revealElements.forEach((element) => {

            element.classList.add(
                "platform-reveal"
            );

            revealObserver.observe(element);

        });

    }

});


/* =========================================================
   VAIRRIEN AUTHENTICATION
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       GET STARTED / SIGNUP
    ====================================================== */

    const signupForm = document.getElementById("signup-form");

    if (signupForm) {

        const nameInput = document.getElementById("full-name");
        const emailInput = document.getElementById("email");
        const passwordInput = document.getElementById("password");
        const confirmPasswordInput =
            document.getElementById("confirm-password");

        const termsInput = document.getElementById("terms");
        const submitButton =
            document.getElementById("signup-button");

        const message =
            document.getElementById("auth-message");


        signupForm.addEventListener("submit", async (event) => {

            event.preventDefault();


            const name = nameInput.value.trim();
            const email = emailInput.value.trim();
            const password = passwordInput.value;
            const confirmPassword =
                confirmPasswordInput.value;


            /* =================================================
               VALIDATION
            ================================================== */

            if (!name || !email || !password || !confirmPassword) {

                showAuthMessage(
                    message,
                    "Please complete all required fields."
                );

                return;
            }


            if (password.length < 8) {

                showAuthMessage(
                    message,
                    "Your password must be at least 8 characters."
                );

                return;
            }


            if (password !== confirmPassword) {

                showAuthMessage(
                    message,
                    "Your passwords do not match."
                );

                return;
            }


            if (!termsInput.checked) {

                showAuthMessage(
                    message,
                    "Please agree to the Terms of Service and Privacy Policy."
                );

                return;
            }


            /* =================================================
               SUBMITTING
            ================================================== */

            const originalButtonText =
                submitButton.textContent;

            submitButton.disabled = true;
            submitButton.textContent = "Creating account...";


            try {

                const { data, error } =
                    await supabaseClient.auth.signUp({

                        email: email,

                        password: password,

                        options: {

                            data: {
                                full_name: name
                            }

                        }

                    });


                if (error) {
                    throw error;
                }


                console.log(
                    "Vairrien signup successful:",
                    data
                );


                showAuthMessage(
                    message,
                    "Account created. Please check your email to confirm your Vairrien account."
                );


                submitButton.textContent =
                    "Check your email";



            } catch (error) {

                console.error(
                    "Vairrien signup error:",
                    error
                );


                showAuthMessage(
                    message,
                    error.message ||
                    "Something went wrong while creating your account."
                );


                submitButton.disabled = false;
                submitButton.textContent =
                    originalButtonText;

            }

        });

    }



    /* =====================================================
       LOGIN
    ====================================================== */

    const loginForm =
        document.getElementById("loginForm");

    if (loginForm) {

        const emailInput =
            document.getElementById("loginEmail");

        const passwordInput =
            document.getElementById("loginPassword");

        const submitButton =
            loginForm.querySelector(".auth-submit");


        loginForm.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();


                const email =
                    emailInput.value.trim();

                const password =
                    passwordInput.value;


                if (!email || !password) {

                    alert(
                        "Please enter your email and password."
                    );

                    return;
                }


                const originalButtonText =
                    submitButton.textContent;

                submitButton.disabled = true;

                submitButton.textContent =
                    "Logging in...";


                try {

                    const { data, error } =
                        await supabaseClient.auth
                            .signInWithPassword({

                                email: email,
                                password: password

                            });


                    if (error) {
                        throw error;
                    }


                    console.log(
                        "Vairrien login successful:",
                        data
                    );


                    /*
                     * TEMPORARY DESTINATION
                     *
                     * We will replace this with the
                     * actual Vairrien workspace/dashboard
                     * once that page is built.
                     */

                    window.location.href =
                        "index.html";


                } catch (error) {

                    console.error(
                        "Vairrien login error:",
                        error
                    );


                    alert(
                        error.message ||
                        "Unable to log in."
                    );


                    submitButton.disabled = false;

                    submitButton.textContent =
                        originalButtonText;

                }

            }
        );

    }



    /* =====================================================
       GOOGLE AUTHENTICATION
    ====================================================== */

    const googleButtons =
        document.querySelectorAll(
            ".auth-google-button, .auth-social-button"
        );


    googleButtons.forEach((button) => {

        button.addEventListener(
            "click",
            async () => {

                try {

                    const { error } =
                        await supabaseClient.auth
                            .signInWithOAuth({

                                provider: "google",

                                options: {

                                    redirectTo:
                                        window.location.origin +
                                        "/index.html"

                                }

                            });


                    if (error) {
                        throw error;
                    }


                } catch (error) {

                    console.error(
                        "Google authentication error:",
                        error
                    );


                    alert(
                        error.message ||
                        "Unable to continue with Google."
                    );

                }

            }
        );

    });

});



/* =========================================================
   AUTH MESSAGE HELPER
========================================================= */

function showAuthMessage(element, text) {

    if (!element) {
        alert(text);
        return;
    }


    element.textContent = text;

    element.style.display = "block";

}