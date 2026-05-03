from __future__ import annotations

import html
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HSQLDB_JAR = Path("/tmp/hsqldb/hsqldb-1.8.0.10.jar")
ODB_NAME = "uspevaemost_po_informatike_tsygankova_darina.odb"


PUPILS = [
    (1, "Иванова", "Анна", "9А", "2010-02-14"),
    (2, "Петров", "Максим", "9Б", "2009-11-03"),
    (3, "Сидорова", "Елена", "8А", "2011-05-21"),
    (4, "Смирнов", "Иван", "8Б", "2011-01-19"),
    (5, "Орлова", "Софья", "9А", "2010-07-08"),
    (6, "Васильев", "Кирилл", "7А", "2012-09-30"),
]

GRADES = [
    (1, 1, 1, 5),
    (2, 1, 2, 4),
    (3, 2, 1, 5),
    (4, 3, 3, 5),
    (5, 4, 2, 4),
    (6, 5, 1, 4),
]

QUERIES = [
    (
        "01_Ученики_сортировка_класс_фамилия",
        'SELECT * FROM "Ученики" ORDER BY "Класс" ASC, "Фамилия" ASC',
    ),
    (
        "02_Ученики_9_класс",
        'SELECT * FROM "Ученики" WHERE "Класс" LIKE \'9%\'',
    ),
    (
        "03_Успеваемость_1_2_четверти",
        'SELECT * FROM "Успеваемость" WHERE "Четверть" IN (1, 2) '
        'ORDER BY "Четверть" ASC, "ID_Оценки" ASC',
    ),
    (
        "04_Девятиклассники_1_четверть_5",
        'SELECT "Ученики"."Фамилия", "Ученики"."Имя", "Ученики"."Класс", '
        '"Успеваемость"."Четверть", "Успеваемость"."Оценка" '
        'FROM "Ученики" INNER JOIN "Успеваемость" '
        'ON "Ученики"."ID_ученика" = "Успеваемость"."ID_ученика" '
        'WHERE "Ученики"."Класс" LIKE \'9%\' '
        'AND "Успеваемость"."Четверть" = 1 '
        'AND "Успеваемость"."Оценка" = 5 '
        'ORDER BY "Ученики"."Фамилия" ASC',
    ),
]


def ensure_hsqldb_jar() -> None:
    if HSQLDB_JAR.exists():
        return
    HSQLDB_JAR.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "curl",
            "-L",
            "--fail",
            "-o",
            str(HSQLDB_JAR),
            "https://repo1.maven.org/maven2/hsqldb/hsqldb/1.8.0.10/hsqldb-1.8.0.10.jar",
        ],
        check=True,
    )


def create_hsqldb_files(workdir: Path) -> Path:
    java_file = workdir / "CreateDb.java"
    java_file.write_text(
        r'''
import java.sql.*;

public class CreateDb {
  public static void main(String[] args) throws Exception {
    Class.forName("org.hsqldb.jdbcDriver");
    Connection c = DriverManager.getConnection("jdbc:hsqldb:file:" + args[0], "sa", "");
    Statement s = c.createStatement();

    s.executeUpdate("CREATE TABLE \"Ученики\" (\"ID_ученика\" INTEGER NOT NULL PRIMARY KEY, \"Фамилия\" VARCHAR(40) NOT NULL, \"Имя\" VARCHAR(40) NOT NULL, \"Класс\" VARCHAR(4) NOT NULL, \"Дата рождения\" DATE NOT NULL)");
    s.executeUpdate("CREATE TABLE \"Успеваемость\" (\"ID_Оценки\" INTEGER NOT NULL PRIMARY KEY, \"ID_ученика\" INTEGER NOT NULL, \"Четверть\" INTEGER NOT NULL, \"Оценка\" INTEGER NOT NULL, CONSTRAINT \"FK_Успеваемость_Ученики\" FOREIGN KEY (\"ID_ученика\") REFERENCES \"Ученики\"(\"ID_ученика\"))");

    String[][] pupils = {
      {"1", "Иванова", "Анна", "9А", "2010-02-14"},
      {"2", "Петров", "Максим", "9Б", "2009-11-03"},
      {"3", "Сидорова", "Елена", "8А", "2011-05-21"},
      {"4", "Смирнов", "Иван", "8Б", "2011-01-19"},
      {"5", "Орлова", "Софья", "9А", "2010-07-08"},
      {"6", "Васильев", "Кирилл", "7А", "2012-09-30"}
    };
    PreparedStatement ps = c.prepareStatement("INSERT INTO \"Ученики\" VALUES (?, ?, ?, ?, ?)");
    for (String[] p : pupils) {
      ps.setInt(1, Integer.parseInt(p[0]));
      ps.setString(2, p[1]);
      ps.setString(3, p[2]);
      ps.setString(4, p[3]);
      ps.setDate(5, java.sql.Date.valueOf(p[4]));
      ps.executeUpdate();
    }

    int[][] grades = {{1,1,1,5}, {2,1,2,4}, {3,2,1,5}, {4,3,3,5}, {5,4,2,4}, {6,5,1,4}};
    ps = c.prepareStatement("INSERT INTO \"Успеваемость\" VALUES (?, ?, ?, ?)");
    for (int[] g : grades) {
      ps.setInt(1, g[0]);
      ps.setInt(2, g[1]);
      ps.setInt(3, g[2]);
      ps.setInt(4, g[3]);
      ps.executeUpdate();
    }

    s.execute("SHUTDOWN SCRIPT");
    c.close();
  }
}
''',
        encoding="utf-8",
    )
    subprocess.run(["javac", "-encoding", "UTF-8", "-cp", str(HSQLDB_JAR), str(java_file)], check=True)
    db_path = workdir / "db" / "uspevaemost"
    subprocess.run(
        [
            "java",
            "-Dfile.encoding=UTF-8",
            "-cp",
            f"{workdir}:{HSQLDB_JAR}",
            "CreateDb",
            str(db_path),
        ],
        check=True,
    )
    return db_path


def content_xml() -> str:
    query_nodes = "\n".join(
        f'<db:query db:name="{html.escape(name)}" db:command="{html.escape(command)}" '
        f'db:escape-processing="true"/>'
        for name, command in QUERIES
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:db="urn:oasis:names:tc:opendocument:xmlns:database:1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.3">
  <office:scripts/>
  <office:font-face-decls/>
  <office:automatic-styles/>
  <office:body>
    <office:database>
      <db:data-source>
        <db:connection-data>
          <db:connection-resource xlink:href="sdbc:embedded:hsqldb"/>
          <db:login db:is-password-required="false"/>
        </db:connection-data>
        <db:driver-settings/>
        <db:application-connection-settings db:is-table-name-length-limited="false" db:append-table-alias-name="false" db:max-row-count="100"/>
      </db:data-source>
      <db:queries>
        {query_nodes}
      </db:queries>
      <db:table-representations>
        <db:table-representation db:name="Ученики">
          <db:columns>
            <db:column db:name="ID_ученика"/>
            <db:column db:name="Фамилия"/>
            <db:column db:name="Имя"/>
            <db:column db:name="Класс"/>
            <db:column db:name="Дата рождения"/>
          </db:columns>
        </db:table-representation>
        <db:table-representation db:name="Успеваемость">
          <db:columns>
            <db:column db:name="ID_Оценки"/>
            <db:column db:name="ID_ученика"/>
            <db:column db:name="Четверть"/>
            <db:column db:name="Оценка"/>
          </db:columns>
        </db:table-representation>
      </db:table-representations>
    </office:database>
  </office:body>
</office:document-content>
'''


def settings_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-settings xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0" office:version="1.3">
  <office:settings>
    <config:config-item-set config:name="ooo:view-settings"/>
    <config:config-item-set config:name="ooo:configuration-settings"/>
  </office:settings>
</office:document-settings>
'''


def meta_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/" office:version="1.3">
  <office:meta>
    <dc:title>Успеваемость по информатике</dc:title>
    <dc:creator>Цыганкова Дарина</dc:creator>
    <meta:generator>LibreOffice Base compatible ODB</meta:generator>
  </office:meta>
</office:document-meta>
'''


def manifest_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.database"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="settings.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="meta.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="database/" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="database/script" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="database/properties" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="forms/" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="reports/" manifest:media-type=""/>
  <manifest:file-entry manifest:full-path="Configurations2/" manifest:media-type=""/>
</manifest:manifest>
'''


def build_odb() -> None:
    ensure_hsqldb_jar()
    out = ROOT / ODB_NAME
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        db_path = create_hsqldb_files(workdir)
        script = db_path.with_suffix(".script").read_bytes()
        properties = db_path.with_suffix(".properties").read_bytes()
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w") as zf:
            zf.writestr("mimetype", "application/vnd.oasis.opendocument.database", compress_type=zipfile.ZIP_STORED)
            for folder in ("forms/", "reports/", "Configurations2/", "META-INF/", "database/"):
                zf.writestr(folder, "", compress_type=zipfile.ZIP_STORED)
            zf.writestr("content.xml", content_xml(), compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("settings.xml", settings_xml(), compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("meta.xml", meta_xml(), compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("database/script", script, compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("database/properties", properties, compress_type=zipfile.ZIP_DEFLATED)
            zf.writestr("META-INF/manifest.xml", manifest_xml(), compress_type=zipfile.ZIP_DEFLATED)


if __name__ == "__main__":
    build_odb()
