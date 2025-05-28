// recommendations.js
document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const form = document.getElementById('recommendation-form');
    const step1Next = document.getElementById('step1-next');
    const step2Next = document.getElementById('step2-next');
    const step2Back = document.getElementById('step2-back');
    const step3Back = document.getElementById('step3-back');
    const submitBtn = document.getElementById('submit-form');
    const budgetInput = document.getElementById('budget');
    const budgetValue = document.getElementById('budget-value');
    
    // Progress tracking
    const steps = document.querySelectorAll('.form-step');
    const progressSteps = document.querySelectorAll('.progress-step');
    const progressBar = document.querySelector('.progress-bar');
    let currentStep = 1;
    
    // Update budget value display
    budgetInput.addEventListener('input', function() {
        budgetValue.textContent = '$' + parseInt(this.value).toLocaleString();
    });
    
    // Navigation between form steps
    step1Next.addEventListener('click', function() {
        goToStep(2);
    });
    
    step2Next.addEventListener('click', function() {
        goToStep(3);
    });
    
    step2Back.addEventListener('click', function() {
        goToStep(1);
    });
    
    step3Back.addEventListener('click', function() {
        goToStep(2);
    });
    
    // Mobile menu toggle
    const menuBtn = document.querySelector('.menu-btn');
    const navLinks = document.querySelector('.nav-links');
    
    if (menuBtn) {
        menuBtn.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }
    
    // Form submission
    if (submitBtn) {
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();
            submitRecommendationForm();
        });
    }
    
    // Function to navigate between steps
    function goToStep(step) {
        // Hide all steps
        steps.forEach(s => s.classList.remove('active'));
        
        // Show the current step
        document.getElementById(`form-step-${step}`).classList.add('active');
        
        // Update progress
        progressSteps.forEach((s, i) => {
            if (i < step) {
                s.classList.add('completed');
            } else {
                s.classList.remove('completed');
            }
            
            if (i + 1 === step) {
                s.classList.add('active');
            } else {
                s.classList.remove('active');
            }
        });
        
        // Update progress bar
        progressBar.style.width = `${((step - 1) / (steps.length - 1)) * 100}%`;
        
        currentStep = step;
    }
    
    // Function to gather form data
    function getFormData() {
        const formData = {
            'region': document.getElementById('region').value,
            'country': document.getElementById('country').value,
            'travel-type': document.querySelector('input[name="travel-type"]:checked').value,
            'group-size': document.getElementById('group-size').value,
            'budget': document.getElementById('budget').value,
            'duration': document.getElementById('duration').value,
            'travel-date': document.getElementById('travel-date').value,
            'destination-type': document.querySelector('input[name="destination-type"]:checked').value,
            'interests': Array.from(document.querySelectorAll('input[name="interests[]"]:checked')).map(el => el.value),
            'accommodation-type': document.getElementById('accommodation-type').value,
            'travel-pace': document.getElementById('travel-pace').value,
            'climate': document.querySelector('input[name="climate"]:checked').value,
            'accessibility': document.getElementById('accessibility').value,
            'dietary': Array.from(document.querySelectorAll('input[name="dietary[]"]:checked')).map(el => el.value),
            'experience-level': document.querySelector('input[name="experience-level"]:checked').value
        };
        
        return formData;
    }
    
    // Function to submit form
    function submitRecommendationForm() {
        // Show loading state
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Generating personalized recommendations...</p>
                </div>
            `;
            resultsContainer.style.display = 'block';
        }
        
        // Get form data
        const formData = getFormData();
        
        // Submit to backend
        fetch('/api/get-recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayRecommendations(data.recommendations);
            } else {
                displayError(data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            displayError(error.toString());
        });
    }

    window.exploreDestination = function(destName) {
        // Redirect to destination details page
        window.location.href = `/destination?name=${encodeURIComponent(destName)}`;
    };
    // Function to display recommendations with collapsible details
// Function to display recommendations with collapsible details
function displayRecommendations(recommendations) {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) return;
    
    // Check if we have destinations
    if (!recommendations.destinations || recommendations.destinations.length === 0) {
        displayError('No recommendations found. Please try with different preferences.');
        return;
    }
    
    // Build HTML for recommendations
    let html = `
        <h2 class="results-title">Your Personalized Travel Recommendations</h2>
        <div class="recommendations-grid">
    `;
    
    // Add each destination with collapsible details
    recommendations.destinations.forEach((dest, index) => {
        html += `
            <div class="recommendation-card" id="card-${index}">
                <div class="card-header">
                    <h3 class="destination-name">${dest.name}</h3>
                    <div class="destination-subtitle">${dest.daily_budget}</div>
                    <button class="expand-btn" onclick="toggleCardDetails(${index})">
                        <span class="expand-icon">▼</span>
                    </button>
                </div>
                
                <div class="card-details" id="details-${index}">
                    <div class="card-body">
                        <p class="destination-description">${dest.description}</p>
                        
                        <h4 class="section-title">Top Attractions</h4>
                        <ul class="attractions-list">
                            ${dest.attractions.map(attr => `<li>${attr}</li>`).join('')}
                        </ul>
                        
                        <div class="destination-details">
                            <div class="detail-item">
                                <span class="detail-label">Best Time to Visit:</span>
                                <span class="detail-value">${dest.best_time}</span>
                            </div>
                        </div>
                        
                        <div class="travel-tips">
                            <h4>Travel Tips</h4>
                            <p>${dest.tips}</p>
                        </div>
                    </div>
                    
                    <div class="card-footer">
                        <button class="explore-btn" onclick="exploreDestination('${dest.name}')">Explore More</button>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += `
        </div>
        <div class="recommendations-actions">
            <button class="refresh-btn" onclick="submitRecommendationForm()">Get New Recommendations</button>
            <button class="save-btn">Save These Recommendations</button>
        </div>
    `;
    
    resultsContainer.innerHTML = html;
    
    // Make sure the toggle function is defined in the global scope
    window.toggleCardDetails = function(index) {
        const details = document.getElementById(`details-${index}`);
        const button = document.querySelector(`#card-${index} .expand-btn .expand-icon`);
        
        if (details.style.display === 'none' || details.style.display === '') {
            details.style.display = 'block';
            button.textContent = '▲';
        } else {
            details.style.display = 'none';
            button.textContent = '▼';
        }
    };
    
    // Make sure submitRecommendationForm is accessible globally
    if (typeof window.submitRecommendationForm !== 'function') {
        window.submitRecommendationForm = submitRecommendationForm;
    }
    
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}
    
    // Function to display error
    function displayError(message) {
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            resultsContainer.innerHTML = `
                <div class="error-message">
                    <h3>Oops! Something went wrong</h3>
                    <p>${message}</p>
                    <button class="retry-btn" onclick="submitRecommendationForm()">Try Again</button>
                </div>
            `;
        }
    }
});