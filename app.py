import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta
from fpdf import FPDF
import io

# --- CORE LOGIC ---

def generate_all_call_data(phone_numbers, start_date, end_date, business_start, business_end, total_calls_per_day, avg_answered_total, jitter_max):
    all_records = []
    total_business_hours = business_end - business_start
    total_business_seconds = total_business_hours * 3600
    
    # Calculate interval
    uniform_interval_seconds = total_business_seconds / total_calls_per_day
    
    remaining_statuses_pool = ["Busy", "Not Answered", "Others"]
    
    # Ensure start_date is a datetime object at midnight
    current_date = datetime.combine(start_date, datetime.min.time())
    # Ensure end_date is a datetime object at midnight
    end_dt = datetime.combine(end_date, datetime.min.time())

    # --- THE FIX: The while loop now correctly increments current_date ---
    while current_date <= end_dt:
        day_start_time = current_date + timedelta(hours=business_start)
        day_end_time = current_date + timedelta(hours=business_end)

        for phone in phone_numbers:
            phone = phone.strip()
            if not phone: continue
            
            lead_id = random.randint(300000, 400000)
            attempt = 1
            
            # Setup statuses for the day
            actual_answered = min(avg_answered_total, total_calls_per_day)
            daily_statuses = ["Answered"] * actual_answered
            remaining_for_this_day = total_calls_per_day - actual_answered
            
            for _ in range(remaining_for_this_day):
                daily_statuses.append(random.choice(remaining_statuses_pool))
            
            random.shuffle(daily_statuses) 
            time_cursor = day_start_time
            
            for call_status in daily_statuses:
                jitter = random.uniform(-jitter_max, jitter_max)
                time_advance = uniform_interval_seconds + jitter
                time_cursor += timedelta(seconds=time_advance)
                
                if time_cursor >= day_end_time:
                    break

                length = random.randint(1, 14) if call_status == "Answered" else 0

                all_records.append({
                    "Date Time": time_cursor.strftime("%d-%m-%Y %H:%M:%S"),
                    "Attempt": attempt,
                    "Lead ID": lead_id,
                    "Status": call_status,
                    "Length (s)": length,
                    "Phone": phone
                })
                attempt += 1
        
        # IMPORTANT: Increment the date to move to the next day
        current_date += timedelta(days=1)
        
    return all_records

def create_pdf_bytes(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Helvetica", size=9)
    
    col_widths = [45, 20, 30, 30, 30, 45]

    def print_row(data, is_header=False):
        if is_header:
            pdf.set_fill_color(200, 220, 255)
            pdf.set_font('Helvetica', 'B', 9)
        else:
            pdf.set_fill_color(255, 255, 255)
            pdf.set_font('Helvetica', '', 9)
        
        for item, width in zip(data, col_widths):
            if pdf.get_y() > 180:
                pdf.add_page()
                print_row(df.columns.tolist(), is_header=True)
            pdf.cell(width, 7, str(item), border=1, ln=0, align='C', fill=True)
        pdf.ln()

    print_row(df.columns.tolist(), is_header=True) 
    
    for row in df.values.tolist():
        if row[3] == "Answered":
            pdf.set_text_color(0, 100, 0)
        else:
            pdf.set_text_color(0, 0, 0)
        print_row(row)
        
    return pdf.output(dest='S').encode('latin-1')

# --- STREAMLIT INTERFACE ---

st.set_page_config(page_title="Call Log Generator", page_icon="📞")
st.title("📞 Call Log PDF Generator")

with st.sidebar:
    st.header("Settings")
    file_name = st.text_input("Output File Name", "call_logs.pdf")
    if not file_name.endswith(".pdf"):
        file_name += ".pdf"
        
    phone_input = st.text_area("Phone Numbers (One per line or comma separated)")
    
    # Date Range Picker
    date_val = st.date_input("Date Range", [datetime.now(), datetime.now() + timedelta(days=2)])
    
    col1, col2 = st.columns(2)
    with col1:
        start_h = st.number_input("Business Start (Hour)", 0, 23, 9)
    with col2:
        end_h = st.number_input("Business End (Hour)", 0, 23, 21)

    total_calls = st.slider("Total Calls Per Day", 1, 1440, 80)
    answered_calls = st.slider("Answered Calls Per Day", 0, total_calls, 7)
    jitter = st.number_input("Jitter (Max Seconds)", 0, 300, 10)

if st.button("Generate Call Logs"):
    if not phone_input:
        st.error("Please enter at least one phone number.")
    elif isinstance(date_val, (list, tuple)) and len(date_val) < 2:
        st.error("Please select both a Start and End date.")
    else:
        numbers = phone_input.replace('\n', ',').split(',')
        numbers = [n.strip() for n in numbers if n.strip()]
        
        # Correctly extract start and end dates from Streamlit input
        start_d = date_val[0]
        end_d = date_val[1]
        
        with st.spinner("Generating data..."):
            try:
                data = generate_all_call_data(numbers, start_d, end_d, start_h, end_h, total_calls, answered_calls, jitter)
                df = pd.DataFrame(data)
                
                if not df.empty:
                    pdf_bytes = create_pdf_bytes(df)
                    st.success(f"Generated {len(df)} records for {len(df['Date Time'].str[:10].unique())} days!")
                    
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name=file_name,
                        mime="application/pdf"
                    )
                    st.dataframe(df)
                else:
                    st.warning("No data generated. Check settings.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
