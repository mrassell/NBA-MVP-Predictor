#Just going to try 2023 season for now 
#Collect data about the season 
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import requests
from bs4 import BeautifulSoup
from io import StringIO
import time


def get_table_content(soup, table_id):
    """Helper function to get table content with debugging"""
    table = soup.find('table', {'id': table_id})
    if table is None:
        print(f"Could not find table with id '{table_id}'")
        print("Available table IDs:")
        for t in soup.find_all('table'):
            print(f"- {t.get('id')}")
        return None
    return table

def get_season_data(year=2023):
    """
    Scrape player statistics for the 2023 season with enhanced debugging
    """
    base_url = "https://www.basketball-reference.com"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # regular season stats
        print("Fetching regular season stats...")
        url = f"{base_url}/leagues/NBA_{year}_per_game.html"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        stats_table = get_table_content(soup, 'per_game_stats')
        if stats_table is None:
            return None
            
        stats_html = StringIO(str(stats_table))
        df = pd.read_html(stats_html)[0]
        print("Successfully retrieved regular season stats")
        
        df = df[df['Rk'] != 'Rk']
        df = df.dropna(subset=['Player'])
        
        print("Fetching advanced stats...")
        time.sleep(1)
        
        advanced_url = f"{base_url}/leagues/NBA_{year}_advanced.html"
        response = requests.get(advanced_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("\nAvailable tables in advanced stats page:")
        for table in soup.find_all('table'):
            print(f"Found table with ID: {table.get('id')}")
        
        advanced_table = get_table_content(soup, 'advanced_stats')
        if advanced_table is None:
            advanced_table = get_table_content(soup, 'advanced')
        
        if advanced_table is None:
            print("Could not find advanced stats table. Creating placeholder stats...")
            df['PER'] = df['PTS'].astype(float) / 30
            df['WS'] = 0
            df['BPM'] = 0
            df['VORP'] = 0
        else:
            advanced_html = StringIO(str(advanced_table))
            advanced_df = pd.read_html(advanced_html)[0]
            print("Successfully retrieved advanced stats")
            
            #clean advanced stats
            advanced_df = advanced_df[advanced_df['Rk'] != 'Rk']
            advanced_df = advanced_df[['Player', 'PER', 'WS', 'BPM', 'VORP']]
            df = pd.merge(df, advanced_df, on='Player', how='left')
        
        #team standings
        print("\nFetching team standings...")
        standings_url = f"{base_url}/leagues/NBA_{year}.html"  # Changed URL
        response = requests.get(standings_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Debug: Print all table IDs
        print("\nAvailable tables in standings page:")
        for table in soup.find_all('table'):
            print(f"Found table with ID: {table.get('id')}")
        
        table_ids = ['divs_standings_E', 'divs_standings_W', 'confs_standings_E']
        standings_tables = []
        
        for table_id in table_ids:
            table = get_table_content(soup, table_id)
            if table is not None:
                standings_html = StringIO(str(table))
                try:
                    standings_df = pd.read_html(standings_html)[0]
                    print(f"\nColumns in {table_id}:")
                    print(standings_df.columns.tolist())
                    standings_tables.append(standings_df)
                except Exception as e:
                    print(f"Error parsing {table_id}: {str(e)}")
        
        if not standings_tables:
            print("No standings tables found. Using default win percentages.")
            df['Win_Pct'] = 0.5
        else:
            #combine East and West standings if we have both
            standings_df = pd.concat(standings_tables, ignore_index=True)
            
            #clean team names and calculate win percentage
            team_col = next((col for col in standings_df.columns if any(x in col.lower() for x in ['team', 'eastern', 'western'])), None)
            
            if team_col is None:
                print("Could not find team column. Using default win percentages.")
                df['Win_Pct'] = 0.5
            else:
                standings_df[team_col] = standings_df[team_col].str.replace('*', '').str.strip()
                standings_df['Win_Pct'] = standings_df['W'].astype(float) / (standings_df['W'].astype(float) + standings_df['L'].astype(float))
                df = pd.merge(df, standings_df[[team_col, 'Win_Pct']], left_on='Tm', right_on=team_col, how='left')
        
        #fill missing win percentages with 0.5
        df['Win_Pct'] = df['Win_Pct'].fillna(0.5)
        
        # Create MVP score
        print("\nCalculating MVP scores...")
        df['MVP_Score'] = (
            df['PTS'].astype(float) * 0.3 +
            df['Win_Pct'].astype(float) * 30 +
            df['PER'].astype(float) * 0.7 +
            df['WS'].astype(float) * 1.5 +
            df['VORP'].astype(float) * 2.0 +
            df['BPM'].astype(float) * 0.8
        )
        
        # Sort score
        df = df.sort_values('MVP_Score', ascending=False)
        
        return df[['Player', 'Tm', 'G', 'MP', 'PTS', 'AST', 'TRB', 'Win_Pct', 
                  'PER', 'WS', 'BPM', 'VORP', 'MVP_Score']]
        
    except Exception as e:
        print(f"\nError processing data: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(traceback.format_exc())
        return None

def main():
    print("Collecting 2023 NBA season data...")
    df = get_season_data(2023)
    
    if df is not None and not df.empty:
        print("\nTop 10 MVP Candidates for 2023 Season:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df.head(10))
        
        df.to_csv('nba_mvp_2023.csv', index=False)
        print("\nData saved to 'nba_mvp_2023.csv'")
    else:
        print("Failed to collect data. Please check the error messages above.")

if __name__ == "__main__":
    main()