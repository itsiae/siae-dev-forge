// SAFE: parameterized query con tenant filter AND id_emittente.
package it.siae.synthetic;

import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.repository.query.Param;

public interface ReportRepositorySafe extends JpaRepository<Object, Long> {

    // SAFE: bind parameter + AND id_emittente from token
    @Query(value = "SELECT * FROM file_logs WHERE id_file = :idFile AND id_emittente = :idEmittente",
           nativeQuery = true)
    Object findByFileIdSafe(@Param("idFile") Long idFile, @Param("idEmittente") Long idEmittente);

    // SAFE: Spring Data method query con tenant filter (no @Query nativeQuery)
    Object findByIdReportAndIdEmittente(Long idReport, Long idEmittente);
}
