// Wave 3 cross-stack porting: Spring Data JPA + @Query nativeQuery con SQL concat (CWE-89 + CWE-639).
// Synthetic minimal repro, no broadcasting code.
package it.siae.synthetic;

import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ReportRepository extends JpaRepository<Object, Long> {

    // VULNERABLE: nativeQuery=true + string concat su input untrusted (SQLi + IDOR)
    @Query(value = "SELECT * FROM file_logs WHERE id_file = " + "?1", nativeQuery = true)
    Object findByFileIdVulnerable(Long idFile);

    // VULNERABLE: nativeQuery WHERE id_file ma senza id_emittente (IDOR)
    @Query(value = "SELECT * FROM report WHERE id_report = ?1", nativeQuery = true)
    Object findByReportId(Long idReport);
}
