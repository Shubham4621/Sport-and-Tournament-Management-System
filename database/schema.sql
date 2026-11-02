-- Sports & Tournament Management System
-- Requires MySQL 8.0.16+ for enforced CHECK constraints.
-- Schema only: no sample data, triggers, or stored procedures.

CREATE DATABASE IF NOT EXISTS sports_tournament_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE sports_tournament_management;

-- Passwords are stored as application-generated one-way hashes only.
CREATE TABLE IF NOT EXISTS Admins (
    admin_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (admin_id),
    CONSTRAINT uq_admins_username UNIQUE (username),
    CONSTRAINT uq_admins_email UNIQUE (email)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Sports (
    sport_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (sport_id),
    CONSTRAINT uq_sports_name UNIQUE (name)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Departments (
    department_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    department_name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    PRIMARY KEY (department_id),
    CONSTRAINT uq_departments_name UNIQUE (department_name)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Students (
    student_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_number VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(254) NULL,
    department_id INT UNSIGNED NULL,
    enrollment_status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id),
    CONSTRAINT uq_students_number UNIQUE (student_number),
    CONSTRAINT uq_students_email UNIQUE (email),
    KEY idx_students_department (department_id),
    CONSTRAINT fk_students_department
        FOREIGN KEY (department_id)
        REFERENCES Departments (department_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Players (
    player_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id INT UNSIGNED NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id),
    CONSTRAINT uq_players_student UNIQUE (student_id),
    CONSTRAINT fk_players_student
        FOREIGN KEY (student_id)
        REFERENCES Students (student_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Player_Sports (
    player_id INT UNSIGNED NOT NULL,
    sport_id INT UNSIGNED NOT NULL,
    eligible_from DATE NOT NULL,
    eligible_to DATE NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_id, sport_id),
    CONSTRAINT chk_player_sports_eligibility_dates
        CHECK (eligible_to IS NULL OR eligible_to >= eligible_from),
    KEY idx_player_sports_sport_player (sport_id, player_id),
    CONSTRAINT fk_player_sports_player
        FOREIGN KEY (player_id)
        REFERENCES Players (player_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_player_sports_sport
        FOREIGN KEY (sport_id)
        REFERENCES Sports (sport_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Teams (
    team_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    sport_id INT UNSIGNED NOT NULL,
    department_id INT UNSIGNED NOT NULL,
    name VARCHAR(150) NOT NULL,
    team_code VARCHAR(50) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id),
    CONSTRAINT uq_teams_sport_department_name
        UNIQUE (sport_id, department_id, name),
    KEY idx_teams_department_sport_name (department_id, sport_id, name),
    KEY idx_teams_sport_active (sport_id, is_active),
    CONSTRAINT fk_teams_sport
        FOREIGN KEY (sport_id)
        REFERENCES Sports (sport_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_teams_department
        FOREIGN KEY (department_id)
        REFERENCES Departments (department_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Team_Memberships (
    team_id INT UNSIGNED NOT NULL,
    player_id INT UNSIGNED NOT NULL,
    membership_from DATE NOT NULL,
    membership_to DATE NULL,
    PRIMARY KEY (team_id, player_id, membership_from),
    CONSTRAINT chk_team_memberships_dates
        CHECK (membership_to IS NULL OR membership_to >= membership_from),
    KEY idx_team_memberships_player_end (player_id, membership_to),
    CONSTRAINT fk_team_memberships_team
        FOREIGN KEY (team_id)
        REFERENCES Teams (team_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_team_memberships_player
        FOREIGN KEY (player_id)
        REFERENCES Players (player_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Tournaments (
    tournament_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    sport_id INT UNSIGNED NOT NULL,
    name VARCHAR(150) NOT NULL,
    competition_format VARCHAR(20) NOT NULL,
    season VARCHAR(40) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'planned',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tournament_id),
    CONSTRAINT uq_tournaments_sport_name_season
        UNIQUE (sport_id, name, season),
    CONSTRAINT chk_tournaments_competition_format
        CHECK (competition_format IN ('team', 'individual')),
    CONSTRAINT chk_tournaments_status
        CHECK (status IN ('planned', 'registration', 'in_progress', 'completed', 'cancelled')),
    CONSTRAINT chk_tournaments_dates
        CHECK (end_date >= start_date),
    KEY idx_tournaments_sport_status_start (sport_id, status, start_date),
    KEY idx_tournaments_public_status_start (is_published, status, start_date),
    CONSTRAINT fk_tournaments_sport
        FOREIGN KEY (sport_id)
        REFERENCES Sports (sport_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Tournament_Scoring_Rules (
    tournament_id INT UNSIGNED NOT NULL,
    points_for_win DECIMAL(8,2) NOT NULL DEFAULT 3.00,
    points_for_draw DECIMAL(8,2) NOT NULL DEFAULT 1.00,
    points_for_loss DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (tournament_id),
    CONSTRAINT chk_scoring_points_non_negative
        CHECK (
            points_for_win >= 0
            AND points_for_draw >= 0
            AND points_for_loss >= 0
        ),
    CONSTRAINT fk_scoring_rules_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES Tournaments (tournament_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Exactly one team or player entry is allowed for each tournament registration.
CREATE TABLE IF NOT EXISTS Tournament_Entries (
    entry_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    tournament_id INT UNSIGNED NOT NULL,
    team_id INT UNSIGNED NULL,
    player_id INT UNSIGNED NULL,
    registered_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'registered',
    PRIMARY KEY (entry_id),
    CONSTRAINT uq_tournament_entries_tournament_team
        UNIQUE (tournament_id, team_id),
    CONSTRAINT uq_tournament_entries_tournament_player
        UNIQUE (tournament_id, player_id),
    CONSTRAINT chk_tournament_entries_one_participant
        CHECK (
            (team_id IS NOT NULL AND player_id IS NULL)
            OR (team_id IS NULL AND player_id IS NOT NULL)
        ),
    CONSTRAINT chk_tournament_entries_status
        CHECK (status IN ('registered', 'withdrawn', 'disqualified')),
    KEY idx_tournament_entries_status (tournament_id, status),
    KEY idx_tournament_entries_team (team_id),
    KEY idx_tournament_entries_player (player_id),
    CONSTRAINT fk_tournament_entries_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES Tournaments (tournament_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_tournament_entries_team
        FOREIGN KEY (team_id)
        REFERENCES Teams (team_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_tournament_entries_player
        FOREIGN KEY (player_id)
        REFERENCES Players (player_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Matches (
    match_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    tournament_id INT UNSIGNED NOT NULL,
    match_number INT UNSIGNED NOT NULL,
    stage VARCHAR(60) NULL,
    round_name VARCHAR(100) NULL,
    scheduled_at DATETIME NULL,
    venue VARCHAR(200) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (match_id),
    CONSTRAINT uq_matches_tournament_number
        UNIQUE (tournament_id, match_number),
    CONSTRAINT chk_matches_status
        CHECK (status IN ('scheduled', 'live', 'completed', 'postponed', 'cancelled')),
    KEY idx_matches_tournament_status_schedule
        (tournament_id, status, scheduled_at),
    CONSTRAINT fk_matches_tournament
        FOREIGN KEY (tournament_id)
        REFERENCES Tournaments (tournament_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Transactional validation must ensure each entry is from the match's tournament.
CREATE TABLE IF NOT EXISTS Match_Entries (
    match_id INT UNSIGNED NOT NULL,
    entry_id INT UNSIGNED NOT NULL,
    PRIMARY KEY (match_id, entry_id),
    KEY idx_match_entries_entry_match (entry_id, match_id),
    CONSTRAINT fk_match_entries_match
        FOREIGN KEY (match_id)
        REFERENCES Matches (match_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT fk_match_entries_tournament_entry
        FOREIGN KEY (entry_id)
        REFERENCES Tournament_Entries (entry_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS Match_Scores (
    match_id INT UNSIGNED NOT NULL,
    entry_id INT UNSIGNED NOT NULL,
    segment_number INT UNSIGNED NOT NULL,
    segment_label VARCHAR(80) NULL,
    numeric_value DECIMAL(12,3) NULL,
    text_value VARCHAR(255) NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (match_id, entry_id, segment_number),
    CONSTRAINT chk_match_scores_positive_segment
        CHECK (segment_number > 0),
    CONSTRAINT chk_match_scores_value_type
        CHECK (
            (numeric_value IS NOT NULL AND text_value IS NULL)
            OR (numeric_value IS NULL AND text_value IS NOT NULL)
        ),
    CONSTRAINT fk_match_scores_match_entry
        FOREIGN KEY (match_id, entry_id)
        REFERENCES Match_Entries (match_id, entry_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

-- result_rank is nullable/positive and intentionally not unique: tied ranks are valid.
CREATE TABLE IF NOT EXISTS Match_Results (
    match_id INT UNSIGNED NOT NULL,
    entry_id INT UNSIGNED NOT NULL,
    outcome VARCHAR(30) NOT NULL,
    result_rank INT UNSIGNED NULL,
    official_note TEXT NULL,
    declared_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (match_id, entry_id),
    CONSTRAINT chk_match_results_positive_rank
        CHECK (result_rank IS NULL OR result_rank > 0),
    KEY idx_match_results_outcome_rank (match_id, outcome, result_rank),
    KEY idx_match_results_entry (entry_id),
    CONSTRAINT fk_match_results_match_entry
        FOREIGN KEY (match_id, entry_id)
        REFERENCES Match_Entries (match_id, entry_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
) ENGINE = InnoDB;

-- Standings are derived from entries, results, and scoring rules, not stored.