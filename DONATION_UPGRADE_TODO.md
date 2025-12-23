# Medicine Donation to NGO Upgrade TODO

## Focus: Dynamic NGO Database & NGO Verification

### Step 1: Create NGO Model (models.py)
- [ ] Add NGO model with fields: name, address, city, state, pincode, email, phone, website, categories_accepted, is_verified, verification_badge, rating, description, operating_hours
- [ ] Add choices for categories_accepted (Medicine, Grocery, Household)
- [ ] Add rating field (1-5 stars)

### Step 2: Update Views (views.py)
- [ ] Modify donate_to_ngo view to query NGO model instead of hardcoded data
- [ ] Add filtering by location (state/city)
- [ ] Add filtering by categories_accepted
- [ ] Pass verification and rating data to template

### Step 3: Update Template (donate_to_ngo.html)
- [ ] Add verification badge display (verified/unverified)
- [ ] Add star rating display
- [ ] Show NGO details in cards with verification status
- [ ] Add filtering options (location, category)

### Step 4: Admin Integration (admin.py)
- [ ] Register NGO model in admin
- [ ] Add list display for verification status and rating
- [ ] Add filters for state, is_verified

### Step 5: Create Migrations
- [ ] Run makemigrations
- [ ] Run migrate

### Step 6: Populate NGO Data
- [ ] Create management command to populate initial NGO data
- [ ] Add sample verified NGOs for testing

### Step 7: Testing
- [ ] Test donation flow with database NGOs
- [ ] Verify verification badges display correctly
- [ ] Test rating display
- [ ] Test filtering functionality
