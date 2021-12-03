import os
import readFiles_D2_EEG
import hashlib
from psycopg2 import connect

def getData(filepath, toJoin):
    """Retrieves and returns experimental data."""

    if "09-1" in filepath:
        expData = readFiles_D2_EEG.joinData(filepath, toJoin[0])
    elif "10-1" in filepath:
        expData = readFiles_D2_EEG.joinData(filepath, toJoin[1])
    else:
        expData = readFiles_D2_EEG.eegData(filepath)

    return expData

def getFilePaths():
    """Retrieves all filepaths from directory and returns a list of paths.

    A toJoin list is used to append files with -1-1.mat suffix, to then be
    appended to its respective -1.mat file data in getData()."""

    directory = 'Dataset2_Preautism_EEG-Data\\EEG-Data\\'
    filepaths = []
    toJoin = []

    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        # checking if it is a file
        if os.path.isfile(f):
            if "-1-1" in f:
                toJoin.append(f)
            else:
                filepaths.append(f)

    return filepaths, toJoin


def insertStatement(insert, conn, cursor):
    """Function to efficiently execute database commands"""

    cursor.execute(insert)
    conn.commit()

def insertStaticData(db_name, db_user, db_password):
    """Inserts data that is common for all entries into the database.

    Insert defined as the command to execute, followed by using the
    insertStatement function to perform the command.
    """

    hashed_user = hashlib.md5(db_user.encode('utf-8')).hexdigest()

    conn = connect(
        dbname=db_name,
        user=db_user,
        host="localhost",
        password=db_password)

    cursor = conn.cursor()

    insert = "INSERT INTO DataSource (Source, timestamp, Name) VALUES ('" + hashed_user + "', current_timestamp, 'EEG');"  # update description
    insertStatement(insert, conn, cursor)
    
def insertData(filepath, db_name, db_user, db_password, experimentalunitnumber, endpointnumber,
               treatmentnumber, DataSourceNumber, toJoin):  # Think datasourcenumber is moved in new version?
    """Inserts data from each file into the database.

    The function is passed the filepath of the file, the experimental
    unit ID, endpoint ID, treatment ID and datasource ID to be used when
    filling the database with the correct inputs.

    Returns endpointnumber and treatment number so that they can be
    iteratively increased whilst populating the vault.
    """

    expData = getData(filepath, toJoin)

    hashed_user = hashlib.md5(db_user.encode('utf-8')).hexdigest()

    conn = connect(
        dbname=db_name,
        user=db_user,
        host="localhost",
        password=db_password)

    cursor = conn.cursor()

    row_count = len(expData.index)

    for i in range(row_count):  # Each row in the data is a new endpoint
        row = expData.loc[i].to_list()
        row = [str(x) for x in row]

        row = ",".join(row)
        row = "{"+row+"}"

        acquisition_time = "NULL"

        insert = "INSERT INTO EndpointHUB (Source, timestamp, ObservedValue, Acquistiontimestamp) VALUES (%s, current_timestamp, %s, %s);"  # update description
        cursor.execute(insert, (hashed_user, row, acquisition_time))
        conn.commit()

    for i in range(row_count):

        insert = "INSERT INTO ObservesLINK (Source, timestamp, ExperimentID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, 2, %s);"
        cursor.execute(insert, [endpointnumber])
        conn.commit()

        insert = "INSERT INTO EndpointUnitLINK (Source, timestamp, ExperimentalUnitID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, %s, %s);"
        cursor.execute(insert, (experimentalunitnumber, endpointnumber))
        conn.commit()

        insert = "INSERT INTO DataSourceLINK (Source, timestamp, EndpointID, DataSourceID) VALUES ('" + hashed_user + "', current_timestamp, %s, %s);"
        cursor.execute(insert, (endpointnumber, DataSourceNumber))
        conn.commit()

        insert = "INSERT INTO Treatments (Source, timestamp, TreatmentID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, %s, %s);"
        cursor.execute(insert, (treatmentnumber, endpointnumber))
        conn.commit()

        # Loop to account for sessionID for each experimental unit
        # and edge cases where files end with "P".

        if filepath[-5] == "1":
            insert = "INSERT INTO MeasuresLINK (Source, timestamp, SessionID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, 1, %s);"
            cursor.execute(insert, [endpointnumber])
            conn.commit()
        elif filepath[-5] == "2":
            insert = "INSERT INTO MeasuresLINK (Source, timestamp, SessionID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, 2, %s);"
            cursor.execute(insert, [endpointnumber])
            conn.commit()
        elif filepath[-5] == "P":
            if filepath[-6] == "1":
                insert = "INSERT INTO MeasuresLINK (Source, timestamp, SessionID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, 1, %s);"
                cursor.execute(insert, [endpointnumber])
                conn.commit()
            elif filepath[-6] == "2":
                insert = "INSERT INTO MeasuresLINK (Source, timestamp, SessionID, EndpointID) VALUES ('" + hashed_user + "', current_timestamp, 2, %s);"
                cursor.execute(insert, [endpointnumber])
                conn.commit()

        endpointnumber += 1

    cursor.close()

    return endpointnumber, treatmentnumber


def populateVault(db_name, db_user, db_password):
    """Populates the vault with the information from all files.

    Data from each file is sequentially extracted and inserted
    into the data vault.
    """

    print("\n*** POPULATING DATA VAULT WITH DATASET 2 - EEG ***")

    insertStaticData(db_name, db_user, db_password)

    filepaths, toJoin = getFilePaths()

    experimentalunitnumber = 11
    DataSourceNumber = 2
    endpointnumber = 575446
    treatmentnumber = 161

    filepath_length = len(filepaths)

    for i in range(filepath_length):
        print("\nUploading", i+1, "of", filepath_length, "...")
        endointnumber_temp, treatmentnumber = insertData(filepaths[i], db_name, db_user, db_password,
                                                         experimentalunitnumber,
                                                         endpointnumber, treatmentnumber, DataSourceNumber, toJoin)

        endpointnumber = endointnumber_temp
        DataSourceNumber = 2
        treatmentnumber += 1
        experimentalunitnumber += 1