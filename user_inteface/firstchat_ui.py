"""
FirstChat UI - Web Interface for the FirstChat System

A modern, minimalist web interface for the FirstChat system that integrates:
- The scraper results (latest scraped profile)
- The FirstChat API for message generation
- A clean, blue and white interface with responsive design

Usage:
  python firstchat_ui.py

This launches a web server at http://localhost:5001 that provides a streamlined
interface for viewing scraped profiles and generating first messages.
"""

import os
import sys
import json
import base64
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import glob

from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import requests

# Initialize Flask app
app = Flask(__name__)

# Folder paths - adjust these if needed
SCRAPER_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper_layer")
SCRAPED_PROFILES_FOLDER = os.path.join(SCRAPER_FOLDER, "scraped_profiles")
API_URL = "http://localhost:8002/generate_message"

# Default user bio
DEFAULT_USER_BIO = "I am a 18 yr old male living in Rochester NY, I am currently a CS student at The Rochester Institute of Technology, I enjoy mountaineering, working out, trail running, camping, learning languages (Chinese, Spanish), working on AI projects . I am also looking for a long term partner who shares my ideals of a healthy balanced life full of exploration and ambition. Straight, 5 foot 11 inches."

# HTML template for the main page
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FirstChat - Personalized Dating App Messages</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        :root {
            --primary: #2563eb;
            --primary-light: #3b82f6;
            --primary-lighter: #60a5fa;
            --primary-dark: #1d4ed8;
            --neutral: #f0f4f8;
            --neutral-dark: #e1e8f0;
            --text-dark: #1e293b;
            --text-light: #ffffff;
            --text-gray: #64748b;
            --success: #10b981;
            --error: #ef4444;
            --border-radius: 12px;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        
        body {
            background-color: var(--neutral);
            color: var(--text-dark);
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: var(--primary);
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .header p {
            color: var(--text-gray);
            font-size: 1.1rem;
        }
        
        .card {
            background-color: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            padding: 24px;
            margin-bottom: 24px;
        }
        
        .section-title {
            font-size: 1.2rem;
            color: var(--primary);
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .profile-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 20px;
        }
        
        .profile-card {
            background-color: white;
            border-radius: var(--border-radius);
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: transform 0.2s ease-in-out;
            cursor: pointer;
            border: 2px solid transparent;
        }
        
        .profile-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary-lighter);
        }
        
        .profile-card.selected {
            border-color: var(--primary);
        }
        
        .profile-card .profile-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        
        .profile-card .profile-info {
            padding: 16px;
        }
        
        .profile-card .profile-name {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .profile-card .profile-date {
            color: var(--text-gray);
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        
        .profile-card .profile-stats {
            display: flex;
            gap: 12px;
            font-size: 0.9rem;
        }
        
        .profile-card .stat {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .profile-card .stat i {
            color: var(--primary);
        }
        
        .btn {
            background-color: var(--primary);
            color: var(--text-light);
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s ease-in-out;
        }
        
        .btn:hover {
            background-color: var(--primary-dark);
        }
        
        .btn:disabled {
            background-color: var(--text-gray);
            cursor: not-allowed;
        }
        
        .btn-secondary {
            background-color: var(--neutral-dark);
            color: var(--text-dark);
        }
        
        .btn-secondary:hover {
            background-color: #d1dae5;
        }
        
        .btn-section {
            display: flex;
            justify-content: flex-end;
            gap: 12px;
            margin-top: 24px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--neutral-dark);
            border-radius: 8px;
            font-size: 1rem;
            line-height: 1.5;
            min-height: 100px;
            resize: vertical;
        }
        
        .form-group textarea:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .settings-group {
            margin-bottom: 16px;
        }
        
        .settings-group label {
            font-weight: 500;
            margin-bottom: 8px;
            display: block;
        }
        
        .radio-group {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .radio-option {
            flex: 1;
            min-width: 100px;
        }
        
        .radio-option input[type="radio"] {
            display: none;
        }
        
        .radio-option label {
            display: block;
            padding: 10px 16px;
            text-align: center;
            background-color: var(--neutral);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
            font-weight: normal;
        }
        
        .radio-option input[type="radio"]:checked + label {
            background-color: var(--primary);
            color: var(--text-light);
        }
        
        .slider-container {
            padding: 8px 0;
        }
        
        .slider {
            width: 100%;
            -webkit-appearance: none;
            height: 8px;
            border-radius: 4px;
            background: var(--neutral-dark);
            outline: none;
        }
        
        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--primary);
            cursor: pointer;
        }
        
        .slider::-moz-range-thumb {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--primary);
            cursor: pointer;
        }
        
        .slider-labels {
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
            color: var(--text-gray);
            font-size: 0.9rem;
        }
        
        .message-container {
            background-color: var(--primary-light);
            color: var(--text-light);
            padding: 20px;
            border-radius: var(--border-radius);
            margin-bottom: 24px;
            position: relative;
        }
        
        .message-text {
            font-size: 1.2rem;
            line-height: 1.6;
            margin-bottom: 16px;
        }
        
        .message-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .copy-btn {
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(255, 255, 255, 0.3);
            border: none;
            border-radius: 4px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: background 0.2s ease-in-out;
        }
        
        .copy-btn:hover {
            background: rgba(255, 255, 255, 0.5);
        }
        
        .copy-btn i {
            color: white;
            font-size: 1.2rem;
        }
        
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
            flex-direction: column;
            gap: 16px;
        }
        
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            border-radius: 50%;
            border-top: 4px solid var(--primary);
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .tabs {
            display: flex;
            margin-bottom: 20px;
        }
        
        .tab {
            padding: 12px 24px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            font-weight: 500;
        }
        
        .tab.active {
            border-bottom-color: var(--primary);
            color: var(--primary);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: var(--success);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            gap: 12px;
            transform: translateY(100px);
            opacity: 0;
            transition: transform 0.3s ease-out, opacity 0.3s ease-out;
            z-index: 1000;
        }
        
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        .toast i {
            font-size: 1.2rem;
        }
        
        .error-toast {
            background-color: var(--error);
        }
        
        .profile-details {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 24px;
        }
        
        .profile-details-left {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .profile-main-image {
            width: 100%;
            aspect-ratio: 3/4;
            object-fit: cover;
            border-radius: var(--border-radius);
        }
        
        .image-selector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
        
        .image-option {
            aspect-ratio: 1;
            overflow: hidden;
            border-radius: 8px;
            cursor: pointer;
            border: 2px solid transparent;
        }
        
        .image-option.selected {
            border-color: var(--primary);
        }
        
        .image-option img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .profile-details-right {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .profile-header {
            display: flex;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .profile-header h2 {
            font-size: 2rem;
            font-weight: 700;
        }
        
        .profile-header .age {
            font-size: 1.5rem;
            color: var(--text-gray);
        }
        
        .profile-section {
            margin-bottom: 16px;
        }
        
        .profile-section-title {
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text-gray);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .profile-section-content {
            font-size: 1.1rem;
            line-height: 1.6;
        }
        
        .interests-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .interest-tag {
            background-color: var(--primary-lighter);
            color: white;
            padding: 6px 12px;
            border-radius: 100px;
            font-size: 0.9rem;
        }
        
        .profile-summary {
            background-color: var(--neutral);
            padding: 16px;
            border-radius: var(--border-radius);
            margin-top: 16px;
        }
        
        .image-gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }
        
        .gallery-image {
            border-radius: 8px;
            overflow: hidden;
            aspect-ratio: 3/4;
            cursor: pointer;
            border: 2px solid transparent;
            transition: border-color 0.2s ease;
        }
        
        .gallery-image.selected {
            border-color: var(--primary);
        }
        
        .gallery-image img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .image-selection-section {
            margin-top: 16px;
        }
        
        .image-selection-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .image-selection-title h3 {
            font-size: 1.1rem;
            color: var(--text-dark);
        }
        
        @media (max-width: 768px) {
            .profile-details {
                grid-template-columns: 1fr;
            }
            
            .profile-details-left {
                max-width: 300px;
                margin: 0 auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FirstChat</h1>
            <p>Generate personalized first messages for dating apps</p>
        </div>
        
        <div class="tabs">
            <div class="tab active" data-tab="profiles">Profiles</div>
            <div class="tab" data-tab="generate">Generate Message</div>
            <div class="tab" data-tab="results" id="resultsTab" style="display: none;">Results</div>
        </div>
        
        <div class="tab-content active" id="profiles-tab">
            <div class="card">
                <div class="section-title">
                    <i class="fas fa-user"></i> Scraped Profiles
                </div>
                
                {% if profiles %}
                <div class="profile-list">
                    {% for profile in profiles %}
                    <div class="profile-card {% if profile.is_latest %}selected{% endif %}" data-profile-id="{{ profile.id }}">
                        <img src="{{ profile.main_image }}" alt="{{ profile.name }}" class="profile-image">
                        <div class="profile-info">
                            <div class="profile-name">{{ profile.name }}, {{ profile.age }}</div>
                            <div class="profile-date">{{ profile.date }}</div>
                            <div class="profile-stats">
                                <div class="stat">
                                    <i class="fas fa-image"></i> {{ profile.image_count }}
                                </div>
                                <div class="stat">
                                    <i class="fas fa-heart"></i> {{ profile.interest_count }}
                                </div>
                                {% if profile.has_message %}
                                <div class="stat">
                                    <i class="fas fa-comment-dots"></i> Yes
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>No profiles found. Run the scraper first to see profiles here.</p>
                {% endif %}
                
                <div class="btn-section">
                    <button class="btn btn-secondary" id="refresh-btn">
                        <i class="fas fa-sync-alt"></i> Refresh
                    </button>
                    <button class="btn" id="view-profile-btn" {% if not profiles %}disabled{% endif %}>
                        <i class="fas fa-eye"></i> View Profile
                    </button>
                </div>
            </div>
            
            {% if selected_profile %}
            <div class="card">
                <div class="section-title">
                    <i class="fas fa-user-circle"></i> Profile Details
                </div>
                
                <div class="profile-details">
                    <div class="profile-details-left">
                        <img src="{{ selected_profile.main_image }}" alt="{{ selected_profile.name }}" class="profile-main-image" id="main-profile-image">
                        
                        <div class="image-selector">
                            {% for image in selected_profile.images[:6] %}
                            <div class="image-option {% if loop.index == 1 %}selected{% endif %}" data-image="{{ image }}">
                                <img src="{{ image }}" alt="Profile image {{ loop.index }}">
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <div class="profile-details-right">
                        <div>
                            <div class="profile-header">
                                <h2>{{ selected_profile.name }}</h2>
                                <span class="age">{{ selected_profile.age }}</span>
                            </div>
                            
                            {% if selected_profile.interests %}
                            <div class="profile-section">
                                <div class="profile-section-title">Interests</div>
                                <div class="interests-list">
                                    {% for interest in selected_profile.interests %}
                                    <div class="interest-tag">{{ interest }}</div>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                            
                            {% for section_name, section_content in selected_profile.sections.items() %}
                            <div class="profile-section">
                                <div class="profile-section-title">{{ section_name }}</div>
                                <div class="profile-section-content">
                                    {% if section_content is mapping %}
                                        {% for key, value in section_content.items() %}
                                        <div><strong>{{ key }}:</strong> {{ value }}</div>
                                        {% endfor %}
                                    {% else %}
                                        {{ section_content }}
                                    {% endif %}
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        
                        <div class="btn-section">
                            <button class="btn" id="generate-for-profile-btn">
                                <i class="fas fa-comment"></i> Generate Message
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}
        </div>
        
        <div class="tab-content" id="generate-tab">
            <div class="card">
                <div class="section-title">
                    <i class="fas fa-cog"></i> Message Settings
                </div>
                
                <form id="message-form">
                    <div class="form-grid">
                        <div>
                            <div class="form-group">
                                <label for="user-bio">Your Bio</label>
                                <textarea id="user-bio" name="user_bio">{{ default_bio }}</textarea>
                            </div>
                            
                            <div class="settings-group">
                                <label>Message Tone</label>
                                <div class="radio-group">
                                    <div class="radio-option">
                                        <input type="radio" id="tone-friendly" name="tone" value="friendly" checked>
                                        <label for="tone-friendly">Friendly</label>
                                    </div>
                                    <div class="radio-option">
                                        <input type="radio" id="tone-witty" name="tone" value="witty">
                                        <label for="tone-witty">Witty</label>
                                    </div>
                                    <div class="radio-option">
                                        <input type="radio" id="tone-flirty" name="tone" value="flirty">
                                        <label for="tone-flirty">Flirty</label>
                                    </div>
                                    <div class="radio-option">
                                        <input type="radio" id="tone-casual" name="tone" value="casual">
                                        <label for="tone-casual">Casual</label>
                                    </div>
                                    <div class="radio-option">
                                        <input type="radio" id="tone-confident" name="tone" value="confident">
                                        <label for="tone-confident">Confident</label>
                                    </div>
                                    <div class="radio-option">
                                        <input type="radio" id="tone-compliment" name="tone" value="compliment">
                                        <label for="tone-compliment">Compliment</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div>
                            <div class="settings-group">
                                <label>Message Length</label>
                                <div class="slider-container">
                                    <input type="range" min="1" max="5" value="1" class="slider" id="sentence-count" name="sentence_count">
                                    <div class="slider-labels">
                                        <span>Short</span>
                                        <span id="sentence-value">1 sentences</span>
                                        <span>Long</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="settings-group">
                                <label>Creativity Level</label>
                                <div class="slider-container">
                                    <input type="range" min="1" max="10" value="7" class="slider" id="creativity" name="creativity">
                                    <div class="slider-labels">
                                        <span>Conservative</span>
                                        <span id="creativity-value">0.7</span>
                                        <span>Creative</span>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="settings-group">
                                <label>Selected Profile</label>
                                <div class="profile-summary" id="selected-profile-summary">
                                    {% if selected_profile %}
                                    <strong>{{ selected_profile.name }}</strong>, {{ selected_profile.age }} - 
                                    {% if selected_profile.interests %}
                                    Interests: {{ selected_profile.interests|join(', ') }}
                                    {% else %}
                                    No interests listed
                                    {% endif %}
                                    {% else %}
                                    No profile selected. Please select a profile from the Profiles tab.
                                    {% endif %}
                                </div>
                            </div>
                            
                            <div class="settings-group">
                                <div class="image-selection-title">
                                    <h3>Selected Images</h3>
                                    <button type="button" class="btn-secondary" id="randomize-images-btn" style="padding: 5px 10px; font-size: 0.9rem" {% if not selected_profile or not selected_profile.images %}disabled{% endif %}>
                                        <i class="fas fa-random"></i> Randomize
                                    </button>
                                </div>
                                
                                {% if selected_profile and selected_profile.images %}
                                <div class="image-gallery" id="image-gallery">
                                    {% for image in selected_profile.images %}
                                    <div class="gallery-image {% if loop.index == 1 %}selected{% endif %}" data-image="{{ image }}" data-index="{{ loop.index0 }}">
                                        <img src="{{ image }}" alt="Profile image {{ loop.index }}">
                                    </div>
                                    {% endfor %}
                                </div>
                                {% else %}
                                <p>No images available</p>
                                {% endif %}
                                
                                <div style="display: flex; margin-top: 16px; gap: 12px;">
                                    <div style="flex: 1;">
                                        <div class="profile-section-title">Primary Image</div>
                                        <div id="primary-image-container" style="border-radius: 8px; overflow: hidden; aspect-ratio: 3/4;">
                                            <img src="{{ selected_profile.images[0] if selected_profile and selected_profile.images else '' }}" alt="Primary image" id="primary-image" style="width: 100%; height: 100%; object-fit: cover;">
                                        </div>
                                    </div>
                                    <div style="flex: 1;">
                                        <div class="profile-section-title">Secondary Image</div>
                                        <div id="secondary-image-container" style="border-radius: 8px; overflow: hidden; aspect-ratio: 3/4;">
                                            <img src="{{ selected_profile.images[1] if selected_profile and selected_profile.images|length > 1 else selected_profile.images[0] if selected_profile and selected_profile.images else '' }}" alt="Secondary image" id="secondary-image" style="width: 100%; height: 100%; object-fit: cover;">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <input type="hidden" id="profile-id" name="profile_id" value="{{ selected_profile.id if selected_profile else '' }}">
                    <input type="hidden" id="image1" name="image1" value="{{ selected_profile.images[0] if selected_profile and selected_profile.images else '' }}">
                    <input type="hidden" id="image2" name="image2" value="{{ selected_profile.images[1] if selected_profile and selected_profile.images|length > 1 else selected_profile.images[0] if selected_profile and selected_profile.images else '' }}">
                    
                    <div class="btn-section">
                        <button type="submit" class="btn" id="generate-btn" {% if not selected_profile %}disabled{% endif %}>
                            <i class="fas fa-comment-dots"></i> Generate Message
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="tab-content" id="results-tab">
            <div class="card">
                <div class="section-title">
                    <i class="fas fa-comment-dots"></i> Generated Message
                </div>
                
                <div id="message-result">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Generating your message...</p>
                    </div>
                </div>
                
                <div class="btn-section">
                    <button class="btn btn-secondary" id="back-to-settings-btn">
                        <i class="fas fa-arrow-left"></i> Back to Settings
                    </button>
                    <button class="btn" id="regenerate-btn" style="background-color: #2563eb;">
                        <i class="fas fa-sync-alt"></i> Regenerate
                    </button>
                    <button class="btn" id="copy-message-btn" disabled>
                        <i class="fas fa-copy"></i> Copy Message
                    </button>
                </div>
            </div>
            
            <div class="card">
                <div class="section-title">
                    <i class="fas fa-info-circle"></i> Message Details
                </div>
                
                <div id="message-details" class="loading">
                    <div class="spinner"></div>
                    <p>Loading details...</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="toast" id="toast">
        <i class="fas fa-check-circle"></i>
        <span id="toast-message">Message copied to clipboard!</span>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // DOM elements
            const tabs = document.querySelectorAll('.tab');
            const tabContents = document.querySelectorAll('.tab-content');
            const profileCards = document.querySelectorAll('.profile-card');
            const viewProfileBtn = document.getElementById('view-profile-btn');
            const generateForProfileBtn = document.getElementById('generate-for-profile-btn');
            const refreshBtn = document.getElementById('refresh-btn');
            const profileIdInput = document.getElementById('profile-id');
            const image1Input = document.getElementById('image1');
            const image2Input = document.getElementById('image2');
            const imageOptions = document.querySelectorAll('.image-option');
            const mainProfileImage = document.getElementById('main-profile-image');
            const generateBtn = document.getElementById('generate-btn');
            const randomizeImagesBtn = document.getElementById('randomize-images-btn');
            const messageForm = document.getElementById('message-form');
            const sentenceSlider = document.getElementById('sentence-count');
            const sentenceValue = document.getElementById('sentence-value');
            const creativitySlider = document.getElementById('creativity');
            const creativityValue = document.getElementById('creativity-value');
            const backToSettingsBtn = document.getElementById('back-to-settings-btn');
            const copyMessageBtn = document.getElementById('copy-message-btn');
            const toast = document.getElementById('toast');
            const toastMessage = document.getElementById('toast-message');
            const resultsTab = document.getElementById('resultsTab');
            const imageGallery = document.getElementById('image-gallery');
            const primaryImage = document.getElementById('primary-image');
            const secondaryImage = document.getElementById('secondary-image');
            
            // Tab functionality
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabId = tab.getAttribute('data-tab');
                    
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    tab.classList.add('active');
                    document.getElementById(`${tabId}-tab`).classList.add('active');
                });
            });
            
            // Profile selection
            let selectedProfileId = profileIdInput.value;
            
            profileCards.forEach(card => {
                card.addEventListener('click', () => {
                    profileCards.forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedProfileId = card.getAttribute('data-profile-id');
                });
            });
            
            // View profile button
            if (viewProfileBtn) {
                viewProfileBtn.addEventListener('click', () => {
                    const selectedCard = document.querySelector('.profile-card.selected');
                    if (selectedCard) {
                        window.location.href = `/profile/${selectedCard.getAttribute('data-profile-id')}`;
                    }
                });
            }
            
            // Generate for profile button
            if (generateForProfileBtn) {
                generateForProfileBtn.addEventListener('click', () => {
                    // Switch to generate tab
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    document.querySelector('[data-tab="generate"]').classList.add('active');
                    document.getElementById('generate-tab').classList.add('active');
                });
            }
            
            // Refresh button
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => {
                    window.location.reload();
                });
            }
            
            // Image option selection
            if (imageOptions) {
                imageOptions.forEach(option => {
                    option.addEventListener('click', () => {
                        const imageSrc = option.getAttribute('data-image');
                        if (mainProfileImage) {
                            mainProfileImage.src = imageSrc;
                        }
                        
                        imageOptions.forEach(o => o.classList.remove('selected'));
                        option.classList.add('selected');
                    });
                });
            }
            
            // Image gallery selection
            if (imageGallery) {
                const galleryImages = imageGallery.querySelectorAll('.gallery-image');
                let selectedPrimaryIndex = 0;
                let selectedSecondaryIndex = galleryImages.length > 1 ? 1 : 0;
                
                galleryImages.forEach(img => {
                    img.addEventListener('click', () => {
                        const imageIndex = parseInt(img.getAttribute('data-index'));
                        const imageSrc = img.getAttribute('data-image');
                        
                        // If primary is being clicked again, do nothing
                        if (selectedPrimaryIndex === imageIndex) {
                            return;
                        }
                        
                        // If secondary is being clicked again, swap primary and secondary
                        if (selectedSecondaryIndex === imageIndex) {
                            const tempIndex = selectedPrimaryIndex;
                            selectedPrimaryIndex = selectedSecondaryIndex;
                            selectedSecondaryIndex = tempIndex;
                            
                            // Update the images
                            if (primaryImage) primaryImage.src = galleryImages[selectedPrimaryIndex].getAttribute('data-image');
                            if (secondaryImage) secondaryImage.src = galleryImages[selectedSecondaryIndex].getAttribute('data-image');
                            
                            // Update hidden inputs
                            image1Input.value = galleryImages[selectedPrimaryIndex].getAttribute('data-image');
                            image2Input.value = galleryImages[selectedSecondaryIndex].getAttribute('data-image');
                            
                            return;
                        }
                        
                        // Otherwise, this is a new selection - make it the secondary image
                        selectedSecondaryIndex = imageIndex;
                        
                        // Update secondary image
                        if (secondaryImage) secondaryImage.src = imageSrc;
                        image2Input.value = imageSrc;
                    });
                });
            }
            
            // Sliders
            if (sentenceSlider) {
                sentenceSlider.addEventListener('input', () => {
                    const value = sentenceSlider.value;
                    sentenceValue.textContent = `${value} sentence${value > 1 ? 's' : ''}`;
                });
            }
            
            if (creativitySlider) {
                creativitySlider.addEventListener('input', () => {
                    const value = (creativitySlider.value / 10).toFixed(1);
                    creativityValue.textContent = value;
                });
            }
            
            // Randomize images button
            if (randomizeImagesBtn) {
                randomizeImagesBtn.addEventListener('click', () => {
                    const selectedProfile = {{ selected_profile_json|safe if selected_profile_json else 'null' }};
                    if (selectedProfile && selectedProfile.images && selectedProfile.images.length > 1) {
                        // Always use Profile Photo 1 for the primary image if available
                        let primaryImageUrl = selectedProfile.images[0];
                        
                        if (selectedProfile.labeled_image_urls && selectedProfile.labeled_image_urls["Profile Photo 1"]) {
                            primaryImageUrl = selectedProfile.labeled_image_urls["Profile Photo 1"];
                        }
                        
                        // Get all other images
                        let secondaryImages = [];
                        
                        // Add all labeled images except the one used for primary
                        if (selectedProfile.labeled_image_urls) {
                            for (const [label, url] of Object.entries(selectedProfile.labeled_image_urls)) {
                                if (url !== primaryImageUrl) {
                                    secondaryImages.push(url);
                                }
                            }
                        }
                        
                        // Add any unlabeled images that aren't already included
                        for (const url of selectedProfile.images) {
                            if (url !== primaryImageUrl && !secondaryImages.includes(url)) {
                                secondaryImages.push(url);
                            }
                        }
                        
                        // If we have secondary images, randomly select one
                        if (secondaryImages.length > 0) {
                            const randomIndex = Math.floor(Math.random() * secondaryImages.length);
                            const secondaryImageUrl = secondaryImages[randomIndex];
                            
                            // Update the UI and form inputs
                            if (primaryImage) primaryImage.src = primaryImageUrl;
                            if (secondaryImage) secondaryImage.src = secondaryImageUrl;
                            
                            image1Input.value = primaryImageUrl;
                            image2Input.value = secondaryImageUrl;
                            
                            showToast("Images randomized!");
                        }
                    }
                });
            }
            
            // Generate message form
            if (messageForm) {
                messageForm.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    if (!profileIdInput.value) {
                        showToast('Please select a profile first', true);
                        return;
                    }
                    
                    // Show results tab
                    resultsTab.style.display = 'block';
                    
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    document.querySelector('[data-tab="results"]').classList.add('active');
                    document.getElementById('results-tab').classList.add('active');
                    
                    // Get form data
                    const formData = new FormData(messageForm);
                    
                    try {
                        // Show loading state
                        document.getElementById('message-result').innerHTML = `
                            <div class="loading">
                                <div class="spinner"></div>
                                <p>Generating your message...</p>
                            </div>
                        `;
                        
                        document.getElementById('message-details').innerHTML = `
                            <div class="loading">
                                <div class="spinner"></div>
                                <p>Loading details...</p>
                            </div>
                        `;
                        
                        // Send request
                        const response = await fetch('/generate', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!response.ok) {
                            throw new Error('Failed to generate message');
                        }
                        
                        const data = await response.json();
                        
                        if (data.status === 'success') {
                            // Update message result
                            document.getElementById('message-result').innerHTML = `
                                <div class="message-container">
                                    <div class="message-text">${data.message}</div>
                                    <button class="copy-btn" id="copy-btn" title="Copy to clipboard">
                                        <i class="fas fa-copy"></i>
                                    </button>
                                    <div class="message-meta">
                                        <span>Generated for: ${data.profile_name}</span>
                                        <span>Generated at: ${new Date().toLocaleTimeString()}</span>
                                    </div>
                                </div>
                            `;
                            
                            // Enable copy button
                            copyMessageBtn.disabled = false;
                            
                            // Set up copy functionality
                            const copyBtn = document.getElementById('copy-btn');
                            if (copyBtn) {
                                copyBtn.addEventListener('click', () => {
                                    navigator.clipboard.writeText(data.message).then(() => {
                                        showToast('Message copied to clipboard!');
                                    });
                                });
                            }
                            
                            // Update message details
                            document.getElementById('message-details').innerHTML = `
                                <div style="display: grid; grid-template-columns: 250px 1fr; gap: 20px;">
                                    <div>
                                        <div class="section-title">Profile Image</div>
                                        <div style="border-radius: 12px; overflow: hidden; margin-top: 10px;">
                                            <img src="${formData.get('image1')}" style="width: 100%; aspect-ratio: 3/4; object-fit: cover;" alt="Profile image">
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <div class="section-title">Image Descriptions</div>
                                        <div style="margin-bottom: 15px;">
                                            ${data.image_tags.map((caption, index) => `
                                                <div style="background-color: var(--primary-lighter); color: white; padding: 10px 15px; border-radius: 8px; margin-bottom: 8px;">
                                                    <strong>Image ${index + 1}:</strong> ${caption}
                                                </div>
                                            `).join('')}
                                        </div>
                                        
                                        <div class="section-title" style="margin-top: 20px;">Settings Used</div>
                                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px;">
                                            <div>
                                                <strong>Tone:</strong> ${data.tone.charAt(0).toUpperCase() + data.tone.slice(1)}
                                            </div>
                                            <div>
                                                <strong>Length:</strong> ${data.sentence_count} sentence${data.sentence_count > 1 ? 's' : ''}
                                            </div>
                                            <div>
                                                <strong>Creativity:</strong> ${data.creativity}
                                            </div>
                                        </div>
                                        
                                        <div class="section-title" style="margin-top: 20px;">Token Usage</div>
                                        <div>
                                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                                <div style="flex: 1; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-right: 10px;">
                                                    <div style="height: 100%; width: ${(data.token_usage.completion_tokens / data.token_usage.total_tokens * 100).toFixed(0)}%; background: var(--primary);"></div>
                                                </div>
                                                <div style="font-size: 13px; color: var(--text-gray); min-width: 100px; text-align: right;">
                                                    ${data.token_usage.completion_tokens} / ${data.token_usage.total_tokens}
                                                </div>
                                            </div>
                                            <div style="font-size: 13px; color: var(--text-gray);">
                                                <strong>Prompt tokens:</strong> ${data.token_usage.prompt_tokens} &nbsp;&nbsp; 
                                                <strong>Response tokens:</strong> ${data.token_usage.completion_tokens} &nbsp;&nbsp;
                                                <strong>Total:</strong> ${data.token_usage.total_tokens}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        } else {
                            throw new Error(data.error || 'Failed to generate message');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        document.getElementById('message-result').innerHTML = `
                            <div style="padding: 20px; color: var(--error);">
                                <i class="fas fa-exclamation-triangle"></i> ${error.message}
                            </div>
                        `;
                        document.getElementById('message-details').innerHTML = `
                            <div style="padding: 20px; color: var(--error);">
                                <i class="fas fa-exclamation-triangle"></i> Failed to load details
                            </div>
                        `;
                        showToast(error.message, true);
                    }
                });
            }
            
            // Back to settings button
            if (backToSettingsBtn) {
                backToSettingsBtn.addEventListener('click', () => {
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    document.querySelector('[data-tab="generate"]').classList.add('active');
                    document.getElementById('generate-tab').classList.add('active');
                });
            }
            
            // Regenerate button
            const regenerateBtn = document.getElementById('regenerate-btn');
            if (regenerateBtn) {
                regenerateBtn.addEventListener('click', async () => {
                    try {
                        // Show loading state
                        document.getElementById('message-result').innerHTML = `
                            <div class="loading">
                                <div class="spinner"></div>
                                <p>Regenerating your message...</p>
                            </div>
                        `;
                        
                        document.getElementById('message-details').innerHTML = `
                            <div class="loading">
                                <div class="spinner"></div>
                                <p>Loading details...</p>
                            </div>
                        `;
                        
                        // Re-send the same form data that was used before
                        const formData = new FormData(messageForm);
                        
                        // Send request
                        const response = await fetch('/generate', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (!response.ok) {
                            throw new Error('Failed to regenerate message');
                        }
                        
                        const data = await response.json();
                        
                        if (data.status === 'success') {
                            // Update message result
                            document.getElementById('message-result').innerHTML = `
                                <div class="message-container">
                                    <div class="message-text">${data.message}</div>
                                    <button class="copy-btn" id="copy-btn" title="Copy to clipboard">
                                        <i class="fas fa-copy"></i>
                                    </button>
                                    <div class="message-meta">
                                        <span>Generated for: ${data.profile_name}</span>
                                        <span>Generated at: ${new Date().toLocaleTimeString()}</span>
                                    </div>
                                </div>
                            `;
                            
                            // Enable copy button
                            copyMessageBtn.disabled = false;
                            
                            // Set up copy functionality
                            const copyBtn = document.getElementById('copy-btn');
                            if (copyBtn) {
                                copyBtn.addEventListener('click', () => {
                                    navigator.clipboard.writeText(data.message).then(() => {
                                        showToast('Message copied to clipboard!');
                                    });
                                });
                            }
                            
                            // Update message details
                            document.getElementById('message-details').innerHTML = `
                                <div style="display: grid; grid-template-columns: 250px 1fr; gap: 20px;">
                                    <div>
                                        <div class="section-title">Profile Image</div>
                                        <div style="border-radius: 12px; overflow: hidden; margin-top: 10px;">
                                            <img src="${formData.get('image1')}" style="width: 100%; aspect-ratio: 3/4; object-fit: cover;" alt="Profile image">
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <div class="section-title">Image Descriptions</div>
                                        <div style="margin-bottom: 15px;">
                                            ${data.image_tags.map((caption, index) => `
                                                <div style="background-color: var(--primary-lighter); color: white; padding: 10px 15px; border-radius: 8px; margin-bottom: 8px;">
                                                    <strong>Image ${index + 1}:</strong> ${caption}
                                                </div>
                                            `).join('')}
                                        </div>
                                        
                                        <div class="section-title" style="margin-top: 20px;">Settings Used</div>
                                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px;">
                                            <div>
                                                <strong>Tone:</strong> ${data.tone.charAt(0).toUpperCase() + data.tone.slice(1)}
                                            </div>
                                            <div>
                                                <strong>Length:</strong> ${data.sentence_count} sentence${data.sentence_count > 1 ? 's' : ''}
                                            </div>
                                            <div>
                                                <strong>Creativity:</strong> ${data.creativity}
                                            </div>
                                        </div>
                                        
                                        <div class="section-title" style="margin-top: 20px;">Token Usage</div>
                                        <div>
                                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                                <div style="flex: 1; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; margin-right: 10px;">
                                                    <div style="height: 100%; width: ${(data.token_usage.completion_tokens / data.token_usage.total_tokens * 100).toFixed(0)}%; background: var(--primary);"></div>
                                                </div>
                                                <div style="font-size: 13px; color: var(--text-gray); min-width: 100px; text-align: right;">
                                                    ${data.token_usage.completion_tokens} / ${data.token_usage.total_tokens}
                                                </div>
                                            </div>
                                            <div style="font-size: 13px; color: var(--text-gray);">
                                                <strong>Prompt tokens:</strong> ${data.token_usage.prompt_tokens} &nbsp;&nbsp; 
                                                <strong>Response tokens:</strong> ${data.token_usage.completion_tokens} &nbsp;&nbsp;
                                                <strong>Total:</strong> ${data.token_usage.total_tokens}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                            
                            showToast('Message regenerated successfully!');
                        } else {
                            throw new Error(data.error || 'Failed to regenerate message');
                        }
                    } catch (error) {
                        console.error('Error:', error);
                        document.getElementById('message-result').innerHTML = `
                            <div style="padding: 20px; color: var(--error);">
                                <i class="fas fa-exclamation-triangle"></i> ${error.message}
                            </div>
                        `;
                        document.getElementById('message-details').innerHTML = `
                            <div style="padding: 20px; color: var(--error);">
                                <i class="fas fa-exclamation-triangle"></i> Failed to load details
                            </div>
                        `;
                        showToast(error.message, true);
                    }
                });
            }
            
            // Copy message button
            if (copyMessageBtn) {
                copyMessageBtn.addEventListener('click', () => {
                    const messageText = document.querySelector('.message-text');
                    if (messageText) {
                        navigator.clipboard.writeText(messageText.textContent).then(() => {
                            showToast('Message copied to clipboard!');
                        });
                    }
                });
            }
            
            // Show toast function
            function showToast(message, isError = false) {
                toast.classList.remove('error-toast');
                if (isError) {
                    toast.classList.add('error-toast');
                }
                
                toastMessage.textContent = message;
                toast.classList.add('show');
                
                setTimeout(() => {
                    toast.classList.remove('show');
                }, 3000);
            }
        });
    </script>
</body>
</html>
"""

def get_scraped_profiles() -> List[Dict[str, Any]]:
    """Get a list of scraped profiles from the scraped_profiles directory."""
    profiles = []
    
    if not os.path.exists(SCRAPED_PROFILES_FOLDER):
        return profiles
    
    # Get all profile directories
    profile_dirs = [d for d in os.listdir(SCRAPED_PROFILES_FOLDER) 
                   if os.path.isdir(os.path.join(SCRAPED_PROFILES_FOLDER, d))]
    
    for profile_dir in profile_dirs:
        # Path to profile data JSON
        profile_path = os.path.join(SCRAPED_PROFILES_FOLDER, profile_dir, "profile_data.json")
        
        if not os.path.exists(profile_path):
            continue
        
        try:
            # Load profile data
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                
            # Check for required fields
            if not profile_data.get("name"):
                continue
                
            # Extract timestamp from directory name
            timestamp = profile_dir.split('_')[-1] if '_' in profile_dir else None
            
            # Get profile images - use direct URLs from labeled_image_urls
            image_urls = []
            if profile_data.get("labeled_image_urls"):
                # Use the direct URLs from the profile data
                image_urls = list(profile_data.get("labeled_image_urls").values())
            elif profile_data.get("image_urls"):
                # Fallback to regular image_urls if available
                image_urls = profile_data.get("image_urls")
                
            # Check if there's a FirstChat message
            has_message = os.path.exists(os.path.join(SCRAPED_PROFILES_FOLDER, profile_dir, "firstchat_message.json"))
            
            # Create profile summary
            profile = {
                "id": profile_dir,
                "name": profile_data.get("name"),
                "age": profile_data.get("age", 0),
                "image_count": len(image_urls),
                "interest_count": len(profile_data.get("interests", [])),
                "date": datetime.fromtimestamp(int(timestamp)) if timestamp and timestamp.isdigit() else "Unknown",
                "main_image": image_urls[0] if image_urls else "/static/placeholder.png",
                "has_message": has_message,
                "is_latest": False  # Will set this on the latest profile later
            }
            
            profiles.append(profile)
            
        except Exception as e:
            print(f"Error processing profile {profile_dir}: {str(e)}")
    
    # Sort by date (newest first) and mark the latest one
    profiles.sort(key=lambda p: p["id"].split('_')[-1] if '_' in p["id"] else "", reverse=True)
    
    if profiles:
        profiles[0]["is_latest"] = True
    
    return profiles

def get_profile_details(profile_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information for a specific profile."""
    if not profile_id:
        return None
        
    profile_path = os.path.join(SCRAPED_PROFILES_FOLDER, profile_id, "profile_data.json")
    
    if not os.path.exists(profile_path):
        return None
        
    try:
        # Load profile data
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
            
        # Get profile images - use direct URLs from labeled_image_urls
        image_urls = []
        
        # Use labeled image URLs directly
        if profile_data.get("labeled_image_urls"):
            image_urls = list(profile_data.get("labeled_image_urls").values())
        elif profile_data.get("image_urls"):
            image_urls = profile_data.get("image_urls")
            
        # Create detailed profile
        detailed_profile = {
            "id": profile_id,
            "name": profile_data.get("name"),
            "age": profile_data.get("age", 0),
            "interests": profile_data.get("interests", []),
            "sections": profile_data.get("profile_sections", {}),
            "images": image_urls,
            "main_image": image_urls[0] if image_urls else "/static/placeholder.png",
            "labeled_image_urls": profile_data.get("labeled_image_urls", {}),  # Include full labeled images dictionary
            "image_urls": profile_data.get("image_urls", [])  # Include original image URLs as backup
        }
        
        return detailed_profile
        
    except Exception as e:
        print(f"Error getting profile details for {profile_id}: {str(e)}")
        return None

def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encode an image to base64."""
    # Clean up the image path - remove leading slash if it exists
    if image_path.startswith('/'):
        image_path = image_path[1:]
        
    # Replace /profile/ with the actual path to the scraped_profiles directory
    if image_path.startswith('profile/'):
        image_path = os.path.join(SCRAPED_PROFILES_FOLDER, image_path[8:])
        
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            encoded = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Error encoding image {image_path}: {str(e)}")
        
        # Try using direct URL
        if image_path.startswith(('http://', 'https://')):
            return image_path
            
        return None

def download_and_encode_image(url: str) -> Optional[str]:
    """Download an image from a URL and encode it to base64."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            encoded = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded}"
        return None
    except Exception as e:
        print(f"Error downloading image {url}: {str(e)}")
        return None

@app.route('/')
def index():
    """Render the homepage with a list of scraped profiles."""
    profiles = get_scraped_profiles()
    selected_profile = None
    selected_profile_json = None
    
    # Get the latest profile if available
    if profiles:
        latest_profile = profiles[0]
        selected_profile = get_profile_details(latest_profile["id"])
        if selected_profile:
            selected_profile_json = json.dumps(selected_profile)
    
    return render_template_string(
        INDEX_HTML,
        profiles=profiles,
        selected_profile=selected_profile,
        selected_profile_json=selected_profile_json,
        default_bio=DEFAULT_USER_BIO
    )

@app.route('/profile/<profile_id>')
def profile_details(profile_id):
    """Render the profile details page."""
    profiles = get_scraped_profiles()
    selected_profile = get_profile_details(profile_id)
    
    if not selected_profile:
        return redirect(url_for('index'))
        
    selected_profile_json = json.dumps(selected_profile)
    
    return render_template_string(
        INDEX_HTML,
        profiles=profiles,
        selected_profile=selected_profile,
        selected_profile_json=selected_profile_json,
        default_bio=DEFAULT_USER_BIO
    )

@app.route('/profile/<path:image_path>')
def serve_profile_image(image_path):
    """Serve profile images."""
    # Construct the absolute path to the image
    full_path = os.path.join(SCRAPED_PROFILES_FOLDER, image_path)
    
    # Check if the file exists
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return open(full_path, 'rb').read()
    else:
        # Return a default placeholder image or a 404
        return "Image not found", 404

@app.route('/generate', methods=['POST'])
def generate_message():
    """Generate a FirstChat message using the API."""
    try:
        # Get form data
        profile_id = request.form.get('profile_id')
        user_bio = request.form.get('user_bio', DEFAULT_USER_BIO)
        tone = request.form.get('tone', 'friendly')
        sentence_count = int(request.form.get('sentence_count', 2))
        creativity = float(request.form.get('creativity', 7)) / 10
        
        # Get profile details
        profile = get_profile_details(profile_id)
        if not profile:
            return jsonify({"status": "error", "error": "Profile not found"}), 404
            
        # Get images - either from form or use the first two from the profile
        image1_url = request.form.get('image1')
        image2_url = request.form.get('image2')
        
        if not image1_url or not image2_url:
            if len(profile["images"]) > 0:
                # Always use "Profile Photo 1" for first image if available
                if "labeled_image_urls" in profile and "Profile Photo 1" in profile["labeled_image_urls"]:
                    image1_url = profile["labeled_image_urls"]["Profile Photo 1"]
                else:
                    image1_url = profile["images"][0]
                    
                # For second image, either use a provided one or pick one randomly from the rest
                if len(profile["images"]) > 1:
                    other_images = [url for url in profile["images"] if url != image1_url]
                    image2_url = random.choice(other_images)
                else:
                    image2_url = image1_url
            else:
                return jsonify({"status": "error", "error": "No images available"}), 400
                
        print(f"Using images: {image1_url} and {image2_url}")
                
        # URLs are already in the correct format for the API - the API client will handle downloading
        # We just need to make sure they're valid URLs
        if not image1_url.startswith(('http://', 'https://')) or not image2_url.startswith(('http://', 'https://')):
            return jsonify({"status": "error", "error": "Invalid image URLs"}), 400
                
        # Prepare match bio
        match_bio = {
            "name": profile["name"],
            "age": profile["age"],
            "bio": "",
            "interests": profile["interests"]
        }
        
        # Build bio from profile sections
        bio_parts = []
        for section_name, section_content in profile["sections"].items():
            if isinstance(section_content, dict):
                section_text = f"{section_name}: " + ", ".join([f"{k}: {v}" for k, v in section_content.items()])
                bio_parts.append(section_text)
            elif isinstance(section_content, str):
                bio_parts.append(f"{section_name}: {section_content}")
                
        match_bio["bio"] = "\n".join(bio_parts)
        
        # Prepare request to FirstChat API
        request_data = {
            "image1": image1_url,
            "image2": image2_url,
            "user_bio": user_bio,
            "match_bio": match_bio,
            "sentence_count": sentence_count,
            "tone": tone,
            "creativity": creativity
        }
        
        # Call the API
        print(f"Sending request to API: {API_URL}")
        response = requests.post(API_URL, json=request_data)
        
        if response.status_code != 200:
            error_msg = f"API returned status code {response.status_code}: {response.text}"
            print(error_msg)
            return jsonify({"status": "error", "error": error_msg}), 500
            
        # Parse the API response
        api_response = response.json()
        
        if api_response.get("status") != "success":
            error_msg = f"API returned an error: {api_response.get('error', 'Unknown error')}"
            print(error_msg)
            return jsonify({"status": "error", "error": error_msg}), 500
            
        # Get the generated message and other data
        message_data = api_response.get("data", {})
        generated_message = message_data.get("generated_message", "No message generated")
        image_tags = message_data.get("image_tags", [])
        token_usage = message_data.get("token_usage", {})
        
        # Save the response to the profile directory
        result_path = os.path.join(SCRAPED_PROFILES_FOLDER, profile_id, "firstchat_message.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(api_response, f, indent=2)
        
        print(f"Saved message to {result_path}")
            
        # Return success with the generated message
        return jsonify({
            "status": "success",
            "message": generated_message,
            "profile_name": profile["name"],
            "image_tags": image_tags,
            "token_usage": token_usage,
            "sentence_count": sentence_count,
            "tone": tone,
            "creativity": creativity
        })
        
    except Exception as e:
        error_msg = f"Error generating message: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "error": error_msg}), 500

@app.route('/static/placeholder.png')
def placeholder_image():
    """Generate a placeholder image."""
    # Return a simple SVG placeholder
    svg = f'''
    <svg xmlns="http://www.w3.org/2000/svg" width="300" height="400" viewBox="0 0 300 400">
        <rect width="300" height="400" fill="#f0f4f8"/>
        <text x="150" y="200" font-family="Arial" font-size="24" fill="#64748b" text-anchor="middle">
            No Image
        </text>
    </svg>
    '''
    return svg, 200, {'Content-Type': 'image/svg+xml'}

def setup_static_folder():
    """Create a static folder for assets if it doesn't exist."""
    static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    os.makedirs(static_folder, exist_ok=True)

if __name__ == "__main__":
    setup_static_folder()
    app.run(host="0.0.0.0", port=5001, debug=True)